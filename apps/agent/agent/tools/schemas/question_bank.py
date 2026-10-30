from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent.tools.schemas.question import Question, QuestionMode

QuestionScope = Literal["all", "public", "mine"]
QuestionDetail = Literal["summary", "full"]


class SearchQuestionsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scope: QuestionScope = Field(
        default="all",
        description="all 同时搜公共题库和我的题库；public 只搜公共题；mine 只搜我的题库。",
    )
    query: str | None = Field(default=None, max_length=100, description="题干模糊搜索。")
    question_type: QuestionMode | None = Field(default=None, description="按题型筛选。")
    knowledge_point_id: str | None = Field(
        default=None,
        max_length=16,
        description="精确匹配主/辅知识点，使用教材目录编号，如 5.8.2。",
    )
    knowledge_point_prefix: str | None = Field(
        default=None,
        max_length=16,
        description="按目录前缀匹配主/辅知识点，如 5 或 5.8。",
    )
    limit: int = Field(default=10, ge=1, le=20)
    offset: int = Field(default=0, ge=0)
    detail: QuestionDetail = Field(
        default="summary",
        description="summary 不返回答案；full 含答案/参考答案，仅用于讲解，API 最多返回 3 条。",
    )


class SaveQuestionInput(BaseModel):
    question: Question = Field(description="要保存到当前学生私有题库的题目。")


class GetQuestionInput(BaseModel):
    question_id: str = Field(
        min_length=1,
        max_length=64,
        description="题库题目 UUID。",
    )


class PracticeQuestionInput(BaseModel):
    question_id: str = Field(
        min_length=1,
        max_length=64,
        description="要练习的题库题目 UUID；必须是当前学生的私有题。",
    )


class ImportQuestionsInput(BaseModel):
    questions: list[Question] = Field(
        min_length=1,
        max_length=5,
        description="从文本或图片解析出的题目；单次最多 5 道。",
    )


class ImportQuestionsResume(BaseModel):
    action: Literal["save", "cancel"]
    questions: list[Question] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def _require_questions_when_saving(self) -> Self:
        if self.action == "save" and not self.questions:
            raise ValueError("保存时至少需要一道题")
        return self
