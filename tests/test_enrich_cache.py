import asyncio
import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from PIL import Image

from config import AmapConfig
from models.schemas import Activity, CultureData, DayPlan, RoutePlan, Spot
from tools import enrich


def valid_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), (34, 92, 71)).save(output, format="PNG")
    return output.getvalue()


class PathAndImageValidationTests(unittest.TestCase):
    def test_paths_are_bounded_for_traversal_windows_paths_and_collisions(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(enrich, "PHOTO_DIR", Path(temp_dir)):
            root = Path(temp_dir).resolve()
            for city, name in [
                ("../outside", "../../secret"),
                (r"C:\Users\someone\photos", r"..\..\secret"),
                ("/tmp/city", "/absolute/name"),
            ]:
                path = enrich._asset_path(city, name)
                self.assertTrue(path.is_relative_to(root))
            self.assertNotEqual(
                enrich._asset_path("城/市", "甲景点"),
                enrich._asset_path("城市", "甲/景点"),
            )
            self.assertIsNone(enrich._path_from_photo_url(
                "/static/photos/%2e%2e/%2e%2e/secret.jpg"
            ))

    def test_complete_small_image_is_valid_but_header_only_or_truncated_image_is_not(self):
        image = valid_png()
        self.assertLess(len(image), 512)
        self.assertTrue(enrich._valid_image_bytes(image))
        self.assertFalse(enrich._valid_image_bytes(b"\x89PNG\r\n\x1a\n" + b"garbage" * 20))
        self.assertFalse(enrich._valid_image_bytes(image[:-12]))


class EnrichmentCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addAsyncCleanup(self._cleanup_temp_dir)
        self.photo_dir = Path(self.temp_dir.name)
        self.index_file = self.photo_dir / "index.json"
        self.photo_patch = patch.object(enrich, "PHOTO_DIR", self.photo_dir)
        self.index_patch = patch.object(enrich, "INDEX_FILE", self.index_file)
        self.photo_patch.start()
        self.index_patch.start()
        self.addCleanup(self.photo_patch.stop)
        self.addCleanup(self.index_patch.stop)

    async def _cleanup_temp_dir(self):
        self.temp_dir.cleanup()

    async def _write_download(self, client, url, dest):
        content = valid_png()
        actual = dest.with_suffix(".png")
        self.assertTrue(enrich._store_image_bytes(actual, content))
        return actual

    async def test_photo_cache_records_provenance_without_source_url_or_credentials(self):
        source_url = "https://store.is.autonavi.com/pic.jpg?key=secret-key&sig=signed-value"
        poi = {
            "coordinate": [116.397, 39.908],
            "photos": [source_url],
            "name": "天安门",
            "poi_id": "amap-poi-123",
        }
        index = {}
        with patch("tools.enrich._poi_search", new=AsyncMock(return_value=poi)), \
             patch("tools.enrich._download_to", new=AsyncMock(side_effect=self._write_download)), \
             patch("tools.enrich._wikimedia_photo", new=AsyncMock(return_value=None)):
            photo, coordinate, record = await enrich._resolve(
                object(), "北京", "天安门", "", index,
                AmapConfig(web_key="server-key", web_secret="server-secret"),
            )

        self.assertEqual(coordinate, [116.397, 39.908])
        self.assertTrue(photo.startswith("/static/photos/"))
        self.assertEqual(record["photo_source"], "amap_poi_photo")
        self.assertEqual(record["photo_source_host"], "store.is.autonavi.com")
        self.assertEqual(record["poi_id"], "amap-poi-123")
        self.assertEqual(record["coordinate_source"], "amap_poi")
        self.assertTrue(record["coordinate_checked_at"])
        self.assertTrue(record["photo_checked_at"])
        self.assertIn("未核验门票", record["verification_boundary"])
        serialized = json.dumps(index, ensure_ascii=False)
        for secret in (source_url, "secret-key", "signed-value", "server-secret"):
            self.assertNotIn(secret, serialized)

    async def test_missing_and_tiny_cached_files_are_refetched(self):
        for corrupt in (False, True):
            cache_key = enrich._cache_key("杭州", "", "西湖")
            path = enrich._asset_path("杭州", "西湖", ".png")
            photo_url = enrich._photo_url("杭州", "西湖", ".png")
            expires = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
            index = {cache_key: {
                "photo": photo_url,
                "photo_source": "amap_poi_photo",
                "photo_source_host": "store.is.autonavi.com",
                "photo_checked_at": datetime.now(timezone.utc).isoformat(),
                "photo_expires_at": expires,
                "coordinate": [120.15, 30.27],
                "coordinate_verified": True,
                "coordinate_source": "amap_poi",
                "coordinate_checked_at": datetime.now(timezone.utc).isoformat(),
                "coordinate_expires_at": expires,
                "poi_id": "old-id",
                "expires_at": expires,
            }}
            if corrupt:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"\x89PNG")
            poi = {
                "coordinate": [120.16, 30.28],
                "photos": ["https://store.is.autonavi.com/new.jpg?key=fake"],
                "name": "西湖",
                "poi_id": "new-id",
            }
            with patch("tools.enrich._poi_search", new=AsyncMock(return_value=poi)), \
                 patch("tools.enrich._download_to", new=AsyncMock(side_effect=self._write_download)), \
                 patch("tools.enrich._wikimedia_photo", new=AsyncMock(return_value=None)):
                photo, coordinate, record = await enrich._resolve(
                    object(), "杭州", "西湖", "", index, AmapConfig(web_key="web-key")
                )
            self.assertTrue(photo)
            self.assertEqual(coordinate, poi["coordinate"])
            self.assertEqual(record["poi_id"], "new-id")
            self.assertTrue(enrich._valid_image_file(path))
            index.clear()

    async def test_cached_coordinate_retry_does_not_renew_coordinate_verification_ttl(self):
        checked_at = (datetime.now(timezone.utc) - timedelta(days=20)).replace(microsecond=0)
        expires_at = (checked_at + timedelta(days=30)).isoformat()
        cache_key = enrich._cache_key("杭州", "", "西湖")
        index = {cache_key: {
            "photo": "",
            "photo_source": "none",
            "photo_expires_at": None,
            "coordinate": [120.15, 30.27],
            "coordinate_verified": True,
            "coordinate_source": "amap_poi",
            "coordinate_checked_at": checked_at.isoformat(),
            "coordinate_expires_at": expires_at,
            "expires_at": expires_at,
            "poi_id": "old-id",
        }}
        with patch("tools.enrich._poi_search", new=AsyncMock(return_value=None)), \
             patch("tools.enrich._wikimedia_photo", new=AsyncMock(return_value=None)), \
             patch("tools.enrich._static_map", new=AsyncMock(return_value=None)):
            _, coordinate, record = await enrich._resolve(
                object(), "杭州", "西湖", "", index, AmapConfig(web_key="web-key")
            )
        self.assertEqual(coordinate, [120.15, 30.27])
        self.assertEqual(record["coordinate_checked_at"], checked_at.isoformat())
        self.assertEqual(record["coordinate_expires_at"], expires_at)
        self.assertEqual(record["expires_at"], expires_at)

        # A newly acquired map image gets its own TTL; it does not make the
        # older coordinate look newly verified.
        index[cache_key]["photo_source"] = "none"
        index[cache_key]["photo"] = ""
        index[cache_key]["photo_expires_at"] = None
        with patch("tools.enrich._poi_search", new=AsyncMock(return_value=None)), \
             patch("tools.enrich._wikimedia_photo", new=AsyncMock(return_value=None)), \
             patch("tools.enrich._static_map", new=AsyncMock(return_value=valid_png())):
            _, coordinate, with_new_photo = await enrich._resolve(
                object(), "杭州", "西湖", "", index, AmapConfig(web_key="web-key")
            )
        self.assertEqual(coordinate, [120.15, 30.27])
        self.assertEqual(with_new_photo["coordinate_checked_at"], checked_at.isoformat())
        self.assertEqual(with_new_photo["coordinate_expires_at"], expires_at)
        self.assertEqual(with_new_photo["photo_source"], "static_map")
        self.assertGreater(
            enrich._timestamp_value(with_new_photo["photo_expires_at"]),
            enrich._timestamp_value(with_new_photo["coordinate_expires_at"]),
        )

    async def test_expired_coordinate_is_refreshed_and_transient_miss_is_not_cached(self):
        cache_key = enrich._cache_key("杭州", "", "西湖")
        old_checked = (datetime.now(timezone.utc) - timedelta(days=60)).replace(microsecond=0)
        old_expiry = (old_checked + timedelta(days=30)).isoformat()
        index = {cache_key: {
            "coordinate": [120.15, 30.27], "coordinate_verified": True,
            "coordinate_source": "amap_poi", "coordinate_checked_at": old_checked.isoformat(),
            "coordinate_expires_at": old_expiry, "expires_at": old_expiry,
            "photo": "", "photo_source": "none",
        }}
        with patch("tools.enrich._poi_search", new=AsyncMock(return_value={
            "coordinate": [120.16, 30.28], "photos": [], "name": "西湖", "poi_id": "fresh-id"
        })), patch("tools.enrich._wikimedia_photo", new=AsyncMock(return_value=None)), \
             patch("tools.enrich._static_map", new=AsyncMock(return_value=None)):
            _, coordinate, record = await enrich._resolve(
                object(), "杭州", "西湖", "", index, AmapConfig(web_key="web-key")
            )
        self.assertEqual(coordinate, [120.16, 30.28])
        self.assertNotEqual(record["coordinate_checked_at"], old_checked.isoformat())
        self.assertGreater(enrich._timestamp_value(record["coordinate_expires_at"]), datetime.now(timezone.utc).timestamp())

        empty_index = {}
        with patch("tools.enrich._poi_search", new=AsyncMock(return_value=None)), \
             patch("tools.enrich._wikimedia_photo", new=AsyncMock(return_value=None)):
            await enrich._resolve(object(), "杭州", "西湖", "", empty_index, AmapConfig(web_key="web-key"))
        self.assertEqual(empty_index, {})

    async def test_no_key_does_not_make_requests_or_persist_a_miss(self):
        index = {}
        with patch("tools.enrich._poi_search", new=AsyncMock()) as poi_search:
            result = await enrich._resolve(object(), "杭州", "西湖", "", index, AmapConfig())
        poi_search.assert_not_awaited()
        self.assertEqual(result[:2], (None, None))
        self.assertEqual(index, {})


class IndexMergeTests(unittest.TestCase):
    def test_concurrent_index_writes_merge_rows_and_keep_valid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(enrich, "PHOTO_DIR", Path(temp_dir)), \
             patch.object(enrich, "INDEX_FILE", Path(temp_dir) / "index.json"):
            def save(index):
                enrich._save_index(index)

            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(save, [
                    {f"key-{number}": {"checked_at": datetime.now(timezone.utc).isoformat(), "value": number}}
                    for number in range(24)
                ]))
            saved = json.loads(enrich.INDEX_FILE.read_text(encoding="utf-8"))
            self.assertEqual(set(saved), {f"key-{number}" for number in range(24)})
            self.assertTrue((Path(temp_dir) / "index.json.lock").exists())


class UntrustedEnrichmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_provided_verification_fields_are_cleared_before_enrichment_failure(self):
        spot = Spot(
            name="西湖", city="杭州", coordinate=[120.15, 30.27], coordinate_verified=True,
            coordinate_source="model", coordinate_checked_at="2030-01-01", poi_id="fake",
            photo="https://example.invalid/fake.jpg", photo_source="amap_poi_photo",
            photo_checked_at="2030-01-01",
        )
        culture = CultureData(city="杭州", cuisine={"must_eat": [{
            "name": "龙井虾仁", "where": "湖畔店", "coordinate": [120.15, 30.27],
            "coordinate_verified": True, "photo": "/static/photos/fake.jpg",
            "photo_source": "wikimedia_commons", "poi_id": "fake",
        }]})
        route = RoutePlan(daily_plan=[DayPlan(
            day=1, city="杭州", city_center=[120.15, 30.27],
            morning=Activity(name="西湖", coordinate=[120.15, 30.27], coordinate_verified=True,
                             coordinate_source="amap_poi", coordinate_checked_at="2030-01-01", poi_id="fake"),
            stay_coordinate=[120.15, 30.27], stay_coordinate_verified=True,
        )])
        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(enrich, "PHOTO_DIR", Path(temp_dir)), \
             patch.object(enrich, "INDEX_FILE", Path(temp_dir) / "index.json"), \
             patch("tools.enrich.httpx.AsyncClient", side_effect=RuntimeError("offline")):
            with self.assertRaisesRegex(RuntimeError, "offline"):
                await enrich.enrich_guide([spot], [culture], route, config=AmapConfig())

        self.assertFalse(spot.coordinate_verified)
        self.assertIsNone(spot.coordinate)
        self.assertEqual(spot.photo, "")
        self.assertEqual(spot.photo_source, "none")
        food = culture.cuisine["must_eat"][0]
        self.assertFalse(food["coordinate_verified"])
        self.assertIsNone(food["coordinate"])
        self.assertEqual(food["photo"], "")
        self.assertEqual(food["photo_source"], "none")
        day = route.daily_plan[0]
        self.assertIsNone(day.city_center)
        self.assertIsNone(day.stay_coordinate)
        self.assertFalse(day.stay_coordinate_verified)
        self.assertFalse(day.morning.coordinate_verified)
        self.assertIsNone(day.morning.coordinate)


if __name__ == "__main__":
    unittest.main()
