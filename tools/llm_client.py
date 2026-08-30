"""
LLM 调用客户端 · 兼容 OpenAI API 格式

封装了 DeepSeek/GLM/Qwen 等任何兼容 OpenAI API 的模型调用。
同时支持普通文本生成和结构化 JSON 输出（对象或数组）。
"""

from openai import AsyncOpenAI

from config import Config, default_config
from tools.json_utils import parse_json


class LLMClient:
    """
    LLM 调用客户端

    核心概念:
    - chat(): 自由文本对话，返回字符串
    - chat_structured(): 结构化输出，强制返回 JSON，自动解析为 dict 或 list
    """

    def __init__(self, config: Config = default_config):
        self.cfg = config
        self.client = AsyncOpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
        )

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        普通对话 · 返回文本

        Args:
            system_prompt: 系统角色设定
            user_prompt: 用户输入
            model: 模型名 (默认用配置里的)
            temperature: 温度 (0=确定, 1=创意)

        Returns:
            LLM 回复的纯文本
        """
        response = await self.client.chat.completions.create(
            model=model or self.cfg.llm.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.cfg.llm.temperature,
            max_tokens=self.cfg.llm.max_tokens,
        )
        return response.choices[0].message.content or ""

    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> dict | list:
        """
        结构化对话 · 强制返回 JSON

        原理: 在 prompt 中要求 LLM 输出纯 JSON，然后用容错解析提取。
        因为 DeepSeek 等模型可能不支持原生 JSON mode，所以用 prompt 约束 + 容错解析。

        注意: 输出可能是对象（意图/路线）也可能是数组（景点/文化列表），
        所以约束语不能写死"以 { 开始"。

        Returns:
            解析后的 dict 或 list
        """
        full_prompt = f"""{system_prompt}

【重要】你必须只输出一个合法的 JSON（对象或数组），不要包含任何 markdown 标记、解释文字或代码块符号。
直接以 {{ 或 [ 开始，以对应的 }} 或 ] 结束。"""

        text = await self.chat(
            system_prompt=full_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=0.3,  # 结构化输出用低温，减少幻觉
        )

        return parse_json(text)


# 单例
_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
