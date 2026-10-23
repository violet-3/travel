"""
Agent 基类 · 所有 Agent 的父类

定义 Agent 的核心行为：接收输入、调用 LangChain 结构化输出并转换结果。

每个具体 Agent 只需要:
- 设置 system_prompt (角色设定)
- 实现 build_user_prompt() (把输入数据转成 LLM 能理解的文本)
- 声明 output_schema (LangChain 使用的 Pydantic schema)
- 实现 parse_output() (把结构化结果转换为业务模型或模型列表)
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from tools.llm_client import LLMClient, get_llm

# 输入可以是文本或 Pydantic 模型，输出可以是模型或模型列表。
I = TypeVar("I")
O = TypeVar("O")


class BaseAgent(ABC, Generic[I, O]):
    """
    Agent 基类

    使用方式:
        class MyAgent(BaseAgent[MyInput, MyOutput]):
            @property
            def output_schema(self):
                return MyOutput

            @property
            def system_prompt(self) -> str:
                return "你是一个..."

            def build_user_prompt(self, input_data: MyInput) -> str:
                return f"请处理: {input_data}"

            def parse_output(self, value) -> MyOutput:
                return value if isinstance(value, MyOutput) else MyOutput.model_validate(value)

        agent = MyAgent()
        result = await agent.run(input_data)
    """

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm if llm is not None else get_llm()
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
    def parse_output(self, value) -> O:
        """把 LangChain 结构化结果转换为业务输出"""
        ...

    async def run(self, input_data: I) -> O:
        """
        执行 Agent 的核心流程:
        input → prompt → LLM → parse → output

        LangChain 根据 output_schema 返回结构化结果；parse_output 负责转换为业务模型。
        具体 Agent 可兼容受支持的 JSON 输入，但必须显式拒绝空、非法和截断结果。
        """
        user_prompt = self.build_user_prompt(input_data)

        raw = await self.llm.chat_structured(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=self.output_schema,
        )

        return self.parse_output(raw)

    @property
    @abstractmethod
    def output_schema(self):
        """Pydantic schema supplied to LangChain structured output."""
        ...
