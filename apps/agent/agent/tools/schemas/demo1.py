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
