"""对话相关模型"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求：指定知识库提问，可携带会话 id 实现多轮"""

    kb_id: int = Field(description="知识库 id")
    message: str = Field(min_length=1, max_length=2000, description="用户问题")
    conversation_id: int | None = Field(default=None, description="会话 id（多轮对话时携带）")


class ConversationOut(BaseModel):
    id: int
    kb_id: int
    kb_name: str = ""
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    source_docs: list[dict[str, Any]] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
