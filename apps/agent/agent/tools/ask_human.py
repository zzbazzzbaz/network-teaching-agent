from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool
from langgraph.types import interrupt
from pydantic import BaseModel, Field


class AskHumanToolInput(BaseModel):
    query: str = Field(description='query: 问题。例如："TCP 三次握手中，第二个报文段的标志位是？"')
    option_list: list[str] = Field(
        min_length=2,
        max_length=6,
        description='option_list: 选项列表。["A. SYN","B. SYN+ACK","C. ACK","D. FIN"]',
    )


class AskHumanPayload(BaseModel):
    type: str = "ask_human"
    query: str
    option_list: list[str]


class AskHumanResume(BaseModel):
    answer: str = Field(min_length=1, description='学生选择的选项，例如 "B"')


def make_ask_human() -> BaseTool:
    @tool(
        args_schema=AskHumanToolInput,
        description=(
            "向学生提问并等待学生作答。"
            "出单选题、引导学生思考时调用。"
            "调用后本次运行会暂停，直到客户端提交答案。"
        ),
    )
    def ask_human(*, query: str, option_list: list[str], runtime: ToolRuntime) -> str:
        thread_id: str = runtime.config["configurable"]["thread_id"]
        print(f"【调试信息】用户线程id:{thread_id}")

        payload = AskHumanPayload(query=query, option_list=option_list)
        result = interrupt(
            payload.model_dump(mode="json"),
            response_schema=AskHumanResume,
        )

        return f"学生答案：{result.answer.strip()}"

    return ask_human
