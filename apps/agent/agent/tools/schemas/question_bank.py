from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
