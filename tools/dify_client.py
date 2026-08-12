"""
Dify 工作流客户端 · 调用你建的三个工作流

Dify API 格式:
  POST /v1/workflows/run
  Header: Authorization: Bearer <api_key>
  Body: {"inputs": {...}, "response_mode": "blocking", "user": "travel-agent"}
"""

import json
import httpx
from config import Config, default_config


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

    # ─── 公共调用方法 ───

    async def _call_workflow(self, inputs: dict, api_key: str) -> dict:
        """调用 Dify 工作流，返回 outputs dict"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": "travel-agent",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/workflows/run",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

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
        return self._parse_json(text)

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
        return self._parse_json(text)

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
        return self._parse_json(text)

    # ─── 工具方法 ───
    @staticmethod
    def _fix_truncated_json(text: str) -> str:
        """修复被截断的 JSON —— 补全缺失的字符串引号和闭合方括号/花括号

        原理: 遍历字符，记录是否在字符串内以及括号栈的状态，
        然后按 LIFO 顺序补全缺失的闭合符号。
        """
        text = text.rstrip().rstrip(",").rstrip()

        # 第一遍: 检查字符串是否被截断（未闭合的引号）
        in_string = False
        escape = False
        for ch in text:
            if escape:
                escape = False
            elif ch == "\\" and in_string:
                escape = True
            elif ch == '"':
                in_string = not in_string
        if in_string:
            text += '"'  # 补上缺失的闭合引号

        # 第二遍: 检查所有括号/花括号是否闭合
        stack = []
        in_string = False
        escape = False
        for ch in text:
            if escape:
                escape = False
            elif ch == "\\" and in_string:
                escape = True
            elif ch == '"':
                in_string = not in_string
            elif not in_string:
                if ch in "{[":  # 记录开括号
                    stack.append(ch)
                elif ch == "}":
                    if stack and stack[-1] == "{":
                        stack.pop()
                elif ch == "]":
                    if stack and stack[-1] == "[":
                        stack.pop()

        # 按反序补全缺失的闭合符
        closers = {"{": "}", "[": "]"}
        for opener in reversed(stack):
            text += closers[opener]

        return text
    @staticmethod
    def _parse_json(text: str) -> dict | list:
        """容错 JSON 解析 - LLM 经常输出格式不完美的 JSON"""
        if isinstance(text, (dict, list)):
            return text
        if not isinstance(text, str):
            raise ValueError(f"Expected string, got {type(text)}")

        text = text.strip()

        # 尝试 1: 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试 2: 提取 markdown 代码块
        import re
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试 3: 找到最外层的 { } 或 [ ]
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start >= 0 and end > start:
                chunk = text[start:end + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    pass

        # 尝试 4: 修复常见错误 (尾部逗号, 单引号等)
        cleaned = text
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)  # 去尾部逗号
        cleaned = re.sub(r"'", '"', cleaned)               # 单引号换双引号
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = cleaned.find(start_char)
            end = cleaned.rfind(end_char)
            if start >= 0 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    pass
        # 尝试 5: 修复被截断的 JSON（补全缺失的引号和闭合括号）
        fixed = DifyClient._fix_truncated_json(text)
        try:
            parsed = json.loads(fixed)
            # 修复后至少能拿到部分数据，比完全失败好
            return parsed
        except json.JSONDecodeError:
            pass

        raise ValueError(f"无法解析 JSON，LLM 原始输出:\n{text[:800]}")
