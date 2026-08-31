"""管理接口（管理员）：统计面板 + 全量对话记录查看

对话记录查看是客服系统的合规刚需：管理员可追溯任意用户的历史问答，
定位服务质量问题（如 FAQ 答案过时导致大量同类提问）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.response import ok
from app.db.session import get_db
from app.models.chat import Conversation, Message
from app.models.kb import Document, Faq, KnowledgeBase
from app.models.user import User
from app.schemas.chat import MessageOut

router = APIRouter(prefix="/admin", tags=["管理"])


@router.get("/stats", summary="统计面板（管理员）")
def stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """知识库数、文档数、FAQ 数、会话数、消息数、今日提问数"""
    today_messages = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(func.date(Message.created_at) == func.curdate())
        .scalar()
        or 0
    )
    return ok(
        {
            "knowledge_base_count": db.query(func.count(KnowledgeBase.id)).scalar() or 0,
            "document_count": db.query(func.count(Document.id)).scalar() or 0,
            "succeeded_document_count": db.query(func.count(Document.id))
            .filter(Document.status == Document.STATUS_SUCCEEDED)
            .scalar()
            or 0,
            "faq_count": db.query(func.count(Faq.id)).scalar() or 0,
            "conversation_count": db.query(func.count(Conversation.id)).scalar() or 0,
            "message_count": db.query(func.count(Message.id)).scalar() or 0,
            "today_message_count": today_messages,
        }
    )


@router.get("/messages", summary="全量对话记录查询（管理员）")
def all_messages(
    username: str | None = Query(default=None, description="按用户名过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """分页查询所有用户的对话消息，可按用户名过滤"""
    query = (
        db.query(Message, User.username)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(User, Conversation.user_id == User.id)
    )
    if username:
        query = query.filter(User.username.like(f"%{username}%"))

    total = query.count()
    rows = (
        query.order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = [
        MessageOut.model_validate(m).model_dump() | {"username": uname}
        for m, uname in rows
    ]
    return ok({"total": total, "page": page, "page_size": page_size, "items": data})
