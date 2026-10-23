"""Small, atomic local storage for generated guides (no database, no credentials)."""

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tools.model_profiles import app_data_dir


class GuideHistoryError(RuntimeError):
    """History storage is unreadable or could not be updated safely."""


_LOCK = threading.RLock()
_HISTORY_ID = re.compile(r"^[0-9a-f]{32}$")


class GuideHistoryStore:
    FILE_NAME = "guide-history.json"
    MAX_ITEMS = 30

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else app_data_dir() / self.FILE_NAME

    def _read_unlocked(self) -> list[dict]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError) as exc:
            raise GuideHistoryError("本地攻略历史无法读取，原文件未修改。") from exc
        if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("items"), list):
            raise GuideHistoryError("本地攻略历史格式无效，原文件未修改。")
        valid = []
        for row in raw["items"]:
            if not isinstance(row, dict) or not _HISTORY_ID.fullmatch(str(row.get("id", ""))):
                continue
            guide = row.get("guide")
            if not isinstance(guide, dict) or not isinstance(guide.get("destinations", []), list):
                continue
            try:
                int(guide.get("days") or 0)
            except (TypeError, ValueError, OverflowError):
                continue
            valid.append(row)
        return valid

    def _file_lock(self):
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_file = None
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_file = lock_path.open("a+b")
            if lock_file.seek(0, os.SEEK_END) == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            return lock_file
        except OSError as exc:
            if lock_file is not None:
                try:
                    lock_file.close()
                except OSError:
                    pass
            raise GuideHistoryError("本机历史目录不可用；当前攻略仍可使用。") from exc

    @staticmethod
    def _unlock(lock_file):
        try:
            try:
                lock_file.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        finally:
            try:
                lock_file.close()
            except OSError:
                pass

    def _write_unlocked(self, rows: list[dict]):
        temp_path = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump({"version": 1, "items": rows}, temp_file, ensure_ascii=False)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, self.path)
        except (OSError, TypeError, ValueError) as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise GuideHistoryError("本地攻略历史保存失败；当前攻略仍可使用。") from exc

    @staticmethod
    def _summary(row: dict) -> dict:
        guide = row["guide"]
        try:
            days = int(guide.get("days") or 0)
        except (TypeError, ValueError, OverflowError) as exc:
            raise GuideHistoryError("本地攻略历史包含无效天数，无法读取。") from exc
        return {
            "id": row["id"],
            "saved_at": row.get("saved_at", ""),
            "title": str(guide.get("title", ""))[:160],
            "destinations": [str(value)[:80] for value in (guide.get("destinations") or [])[:12]],
            "days": days,
            "generated_at": str(guide.get("generated_at", ""))[:40],
        }

    def save(self, guide: dict, history_id: str | None = None) -> str:
        if not isinstance(guide, dict):
            raise GuideHistoryError("攻略内容无效，未写入历史。")
        row_id = history_id or uuid.uuid4().hex
        if not _HISTORY_ID.fullmatch(str(row_id)):
            raise GuideHistoryError("历史记录编号无效。")
        row = {
            "id": row_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "guide": guide,
        }
        with _LOCK:
            lock_file = self._file_lock()
            try:
                rows = self._read_unlocked()
                rows = [existing for existing in rows if existing.get("id") != row_id]
                rows.insert(0, row)
                self._write_unlocked(rows[:self.MAX_ITEMS])
            finally:
                self._unlock(lock_file)
        return row_id

    def list(self) -> list[dict]:
        with _LOCK:
            return [self._summary(row) for row in self._read_unlocked()]

    def get(self, history_id: str) -> dict | None:
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            return None
        with _LOCK:
            row = next((row for row in self._read_unlocked() if row["id"] == history_id), None)
            return dict(row["guide"]) if row else None

    def delete(self, history_id: str) -> bool:
        if not isinstance(history_id, str) or not _HISTORY_ID.fullmatch(history_id):
            return False
        with _LOCK:
            lock_file = self._file_lock()
            try:
                rows = self._read_unlocked()
                remaining = [row for row in rows if row["id"] != history_id]
                if len(remaining) == len(rows):
                    return False
                self._write_unlocked(remaining)
                return True
            finally:
                self._unlock(lock_file)
