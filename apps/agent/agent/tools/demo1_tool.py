from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool
from langgraph.types import interrupt

from agent.tools.schemas.demo1 import AskHumanPayload, AskHumanResume, AskHumanToolInput


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
