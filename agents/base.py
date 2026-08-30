"""
Agent 基类 · 所有 Agent 的父类

定义了 Agent 的核心行为:
1. 接收输入 → 2. 调用 LLM → 3. 解析输出 → 4. 返回结构化结果

每个具体 Agent 只需要:
- 设置 system_prompt (角色设定)
- 实现 build_user_prompt() (把输入数据转成 LLM 能理解的文本)
- 实现 parse_output() (把 LLM 文本转成 Pydantic 模型)
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel
from tools.llm_client import LLMClient, get_llm

# 泛型: Input 是输入模型, Output 是输出模型
I = TypeVar("I", bound=BaseModel)
O = TypeVar("O", bound=BaseModel)


class BaseAgent(ABC, Generic[I, O]):
    """
    Agent 基类

    使用方式:
        class MyAgent(BaseAgent[MyInput, MyOutput]):
            @property
            def system_prompt(self) -> str:
                return "你是一个..."

            def build_user_prompt(self, input_data: MyInput) -> str:
                return f"请处理: {input_data}"

            def parse_output(self, text: str) -> MyOutput:
                data = json.loads(text)
                return MyOutput(**data)

        agent = MyAgent()
        result = await agent.run(input_data)
    """

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or get_llm()
        self._name = self.__class__.__name__

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Agent 的角色设定 (System Prompt)"""
        ...

    @abstractmethod
    def build_user_prompt(self, input_data: I) -> str:
        """把输入数据转成给 LLM 的文本"""
        ...

    @abstractmethod
    def parse_output(self, text: str) -> O:
        """把 LLM 返回的文本解析为结构化输出"""
        ...

    async def run(self, input_data: I) -> O:
        """
        执行 Agent 的核心流程:
        input → prompt → LLM → parse → output

        所有 Agent 的输出都是 JSON（对象或数组），统一走 chat_structured，
        由 llm_client + json_utils 做容错解析（剥 markdown 代码块、修截断等）。
        """
        user_prompt = self.build_user_prompt(input_data)

        raw = await self.llm.chat_structured(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )

        return self.parse_output(raw)
