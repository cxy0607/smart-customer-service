"""对话接口：SSE 流式问答 + 会话/消息管理

流式实现说明（面试必考，务必掌握）：
- 为什么用 SSE 而不是 WebSocket？
  AI 回答是单向推送（服务端->客户端），SSE 基于普通 HTTP 单次请求即可实现，
  无需维护双向连接，实现简单、天然支持断线重连、可被代理/网关缓存；
  WebSocket 适合需要客户端频繁上行（如多人协作）的双向场景，此处属于过度设计
- 响应头 Content-Type: text/event-stream，事件分帧见 services/chat_service.py
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import BusinessError, ErrorCode
from app.core.response import ok
from app.db.session import get_db
from app.models.chat import Conversation, Message
from app.models.kb import KnowledgeBase
from app.models.user import User
from app.schemas.chat import ChatRequest, ConversationOut, MessageOut
from app.services.chat_service import chat_stream

router = APIRouter(tags=["对话"])


@router.post("/chat", summary="智能问答（SSE 流式）")
def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
):
    """发起对话：返回 SSE 事件流（meta / delta / done / error）"""
    return StreamingResponse(
        chat_stream(user, req.kb_id, req.message, req.conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",          # 流式响应禁止缓存
            "X-Accel-Buffering": "no",            # 若经 nginx 反代，禁用缓冲保证逐字推送
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations", summary="我的会话列表")
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(Conversation, KnowledgeBase.name)
        .join(KnowledgeBase, Conversation.kb_id == KnowledgeBase.id)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    data = [
        ConversationOut.model_validate(c).model_dump() | {"kb_name": kb_name}
        for c, kb_name in rows
    ]
    return ok(data)


@router.get("/conversations/{conversation_id}/messages", summary="会话消息记录（含引用来源）")
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 会话归属校验：只能看自己的会话
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise BusinessError(ErrorCode.NOT_FOUND, "会话不存在")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ok([MessageOut.model_validate(m).model_dump() for m in messages])


@router.delete("/conversations/{conversation_id}", summary="删除会话")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise BusinessError(ErrorCode.NOT_FOUND, "会话不存在")
    # 消息级联删除（外键 ondelete=CASCADE）
    db.delete(conversation)
    db.commit()
    return ok(message="会话已删除")
