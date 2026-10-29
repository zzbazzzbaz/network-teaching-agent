from pydantic import BaseModel, ConfigDict, Field

from agent.tools.schemas.question import AskQuestion


class AskStudentInput(BaseModel):
    question: AskQuestion = Field(description="要展示给学生的题目。")


class AskStudentResume(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    answer: str = Field(
        min_length=1,
        max_length=2000,
        description='学生答案。单选题传字母，例如 "B"；简答题传文本。',
    )
