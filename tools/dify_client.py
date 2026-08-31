"""
Dify 工作流客户端 · 调用你建的三个工作流

Dify API 格式:
  POST /v1/workflows/run
  Header: Authorization: Bearer <api_key>
  Body: {"inputs": {...}, "response_mode": "blocking", "user": "travel-agent"}
"""

import asyncio
import json
import httpx

from config import Config, default_config
from tools.json_utils import parse_json


class DifyClient:
    """
    Dify 工作流调用客户端

    使用方式:
        client = DifyClient(config)
        intent = await client.call_intent_parser("想去安阳玩3天")
    """

    def __init__(self, config: Config = default_config):
        self.cfg = config
        self.base_url = config.dify.base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """共享连接池，避免每次调用都重建 TCP 连接"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return self._client

    # ─── 公共调用方法 ───

    async def _call_workflow(self, inputs: dict, api_key: str) -> dict:
        """调用 Dify 工作流，返回 outputs dict（网络/服务端错误自动重试一次）"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": "travel-agent",
        }

        last_err: Exception | None = None
        for attempt in (1, 2):
            try:
                client = await self._get_client()
                resp = await client.post(
                    f"{self.base_url}/workflows/run",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                last_err = e
                if attempt == 1:
                    print(f"[Dify] request failed ({e}), retrying once...")
                    await asyncio.sleep(1.5)
        else:
            raise last_err  # type: ignore[misc]

        # Dify workflow API 返回格式可能是:
        # {"data": {"outputs": {"text": "..."}}}
        # 或 {"data": {"id": "...", "outputs": {"text": "..."}}}
        # 或 {"workflow_run_id": "...", "data": {"outputs": {...}}}
        inner = data.get("data", data)
        if inner is None:
            inner = data

        outputs = inner.get("outputs", {})
        if not outputs:
            # 可能 outputs 就在顶层
            outputs = data.get("outputs", {})

        return outputs

    # ─── 三个工作流的封装 ───

    async def call_intent_parser(self, user_input: str) -> dict:
        """意图解析器: 用户文本 → 结构化意图 JSON"""
        print("[IntentParser] Calling...")
        outputs = await self._call_workflow(
            inputs={"user_inputs": user_input},
            api_key=self.cfg.dify.get_key("intent"),
        )
        text = outputs.get("text", outputs.get("output", "{}"))
        print("[IntentParser] Call OK")
        if text and text.strip() not in ("{}", "[]", ""):
            print(f"[IntentParser] Content: {text[:100]}...")
        else:
            print("[IntentParser] WARNING: empty response")
        return parse_json(text)

    async def call_route_planner(self, intent: dict) -> dict:
        """路线规划器: 意图 JSON → 路线 JSON"""
        print("[RoutePlanner] Calling...")
        outputs = await self._call_workflow(
            inputs={
                "destinations": ", ".join(intent.get("destinations", [])),
                "days": intent.get("days", 3),
                "budget_level": intent.get("budget_level", "中等"),
                "pace": intent.get("pace", "不紧不慢"),
                "preferences": json.dumps(intent.get("preferences", []), ensure_ascii=False),
                "constraints": json.dumps(intent.get("constraints", []), ensure_ascii=False),
            },
            api_key=self.cfg.dify.get_key("route"),
        )
        text = outputs.get("text", outputs.get("output", "{}"))
        print("[RoutePlanner] Call OK")
        if text and text.strip() not in ("{}", "[]", ""):
            print(f"[RoutePlanner] Content: {text[:100]}...")
        else:
            print("[RoutePlanner] WARNING: empty response")
        return parse_json(text)

    async def call_content_generator(self, route_json: str, preferences: str = "") -> dict:
        """内容生成器: 路线 JSON → 景点 + 文化 JSON"""
        print("[ContentGen] Calling...")
        outputs = await self._call_workflow(
            inputs={
                "route_json": route_json,
                "preferences": preferences,
            },
            api_key=self.cfg.dify.get_key("content"),
        )
        text = outputs.get("text", outputs.get("output", "[]"))
        print("[ContentGen] Call OK")
        if text and text.strip() not in ("{}", "[]", ""):
            print(f"[ContentGen] Content: {text[:100]}...")
        else:
            print("[ContentGen] WARNING: empty response")
        return parse_json(text)
