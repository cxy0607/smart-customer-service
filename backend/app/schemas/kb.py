"""知识库/文档/FAQ 相关模型"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import UTCDateTimeModel


# ===== 知识库 =====
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="知识库名称")
    description: str = Field(default="", max_length=500, description="描述")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class KnowledgeBaseOut(UTCDateTimeModel):
    id: int
    name: str
    description: str
    created_at: datetime
    # 关联统计（列表接口填充）
    document_count: int = 0
    faq_count: int = 0

    model_config = {"from_attributes": True}


# ===== 文档 =====
class DocumentOut(UTCDateTimeModel):
    id: int
    kb_id: int
    filename: str
    size: int
    status: str
    chunk_count: int
    error_msg: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ===== FAQ =====
class FaqCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500, description="标准问题")
    answer: str = Field(min_length=1, description="预设答案")


class FaqUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=500)
    answer: str | None = Field(default=None, min_length=1)


class FaqOut(UTCDateTimeModel):
    id: int
    kb_id: int
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}
