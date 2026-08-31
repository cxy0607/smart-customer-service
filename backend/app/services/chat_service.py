"""对话服务：智能客服核心业务流程

处理流程（本项目的核心设计，面试必讲）：
   用户提问 -> 限流检查 -> FAQ 向量匹配
     ├─ 命中（相似度 >= 阈值）：直接返回预设答案【零 token 成本、毫秒级响应、答案 100% 可控】
     └─ 未命中：RAG 检索知识库 -> LLM 流式生成【答案基于知识库内容，防幻觉】

SSE 事件协议（与前端约定的流式协议）：
    event: meta   data: {conversation_id, title, match_type, sources}  # 元信息+引用来源
    event: delta  data: {text}                                          # 文本增量（逐字）
    event: done   data: {answer, message_id}                            # 结束（完整答案）
    event: error  data: {code, message}                                 # 业务错误
"""
import json
from typing import Iterator

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import BusinessError, ErrorCode
from app.core.logger import get_logger
from app.core.rate_limit import check_rate_limit
from app.models.chat import Conversation, Message
from app.models.kb import KnowledgeBase
from app.models.user import User
from app.rag.pipeline import retrieve, stream_generate
from app.rag.vectorstore import match_faq

logger = get_logger()
settings = get_settings()


def sse(event: str, data: dict) -> str:
    """把事件编码为 SSE 文本帧（json 不转义中文，保证流式可读）"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sources_from_docs(docs: list) -> list[dict]:
    """检索结果转换为前端展示的引用来源结构"""
    return [
        {
            "source": doc.metadata.get("source", "未知来源"),
            "page": doc.metadata.get("page"),
            "content": doc.page_content[:200],  # 截断展示，完整内容在库中
            "score": round(score, 4),
        }
        for doc, score in docs
    ]


def chat_stream(
    user: User,
    kb_id: int,
    message: str,
    conversation_id: int | None,
) -> Iterator[str]:
    """对话主流程：SSE 事件流生成器

    生成器内自建数据库会话（流式响应生命周期长，不能用请求级 Session）
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        # ===== 1. 校验知识库 =====
        kb = db.get(KnowledgeBase, kb_id)
        if kb is None:
            yield sse("error", {"code": ErrorCode.NOT_FOUND, "message": "知识库不存在"})
            return

        # ===== 2. 限流（每用户每分钟 N 次，Redis 滑动窗口）=====
        if not check_rate_limit(
            f"chat:{user.id}", settings.RATE_LIMIT_CHAT_PER_MINUTE
        ):
            yield sse("error", {"code": ErrorCode.RATE_LIMITED, "message": "提问过于频繁，请稍后再试"})
            return

        # ===== 3. 会话处理：复用或新建，并加载多轮历史 =====
        if conversation_id is not None:
            conversation = db.get(Conversation, conversation_id)
            if conversation is None or conversation.user_id != user.id:
                yield sse("error", {"code": ErrorCode.NOT_FOUND, "message": "会话不存在"})
                return
        else:
            # 新会话：标题取问题前 30 字
            conversation = Conversation(
                user_id=user.id,
                kb_id=kb_id,
                title=message[:30] + ("..." if len(message) > 30 else ""),
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        # 加载多轮历史（用于 LLM 理解上下文，最近 N 条）
        history = [
            {"role": m.role, "content": m.content}
            for m in db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(settings.CHAT_HISTORY_LIMIT)
            .all()
        ][::-1]  # 反转为时间正序

        # 用户消息先落库（无论后续成功与否，用户说了什么都要留痕）
        user_msg = Message(conversation_id=conversation.id, role="user", content=message)
        db.add(user_msg)
        db.commit()

        # ===== 4. FAQ 优先匹配 =====
        faq_hit = None
        try:
            faq_hit = match_faq(kb_id, message, settings.FAQ_SIMILARITY_THRESHOLD)
        except Exception as e:
            # FAQ 匹配失败不阻断对话（降级走 RAG），记录日志便于排查
            logger.warning(f"FAQ 匹配异常，降级走 RAG | kb={kb_id} error={e}")

        if faq_hit:
            # ===== 命中 FAQ：直接返回预设答案 =====
            from app.models.kb import Faq

            faq_id, similarity = faq_hit
            faq = db.get(Faq, faq_id)
            yield sse(
                "meta",
                {
                    "conversation_id": conversation.id,
                    "title": conversation.title,
                    "match_type": "faq",  # 前端据此展示"已自动匹配常见问题"
                    "sources": [{"source": "FAQ", "faq_id": faq_id, "score": round(similarity, 4)}],
                },
            )
            yield sse("delta", {"text": faq.answer})
            # FAQ 答案落库
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=faq.answer,
                source_docs=[{"source": "FAQ", "faq_id": faq_id}],
            )
            db.add(assistant_msg)
            db.commit()
            yield sse("done", {"answer": faq.answer, "message_id": assistant_msg.id})
            logger.info(f"FAQ 命中 | kb={kb_id} faq={faq_id} similarity={similarity:.3f}")
            return

        # ===== 5. 未命中 FAQ：RAG 检索 + 流式生成 =====
        docs = retrieve(kb_id, message)
        yield sse(
            "meta",
            {
                "conversation_id": conversation.id,
                "title": conversation.title,
                "match_type": "rag",
                "sources": _sources_from_docs(docs),
            },
        )

        # 流式生成（逐段产出 token）
        answer_parts: list[str] = []
        for token in stream_generate(message, docs, history):
            answer_parts.append(token)
            yield sse("delta", {"text": token})

        answer = "".join(answer_parts)
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            source_docs=_sources_from_docs(docs) or None,
        )
        db.add(assistant_msg)
        db.commit()
        yield sse("done", {"answer": answer, "message_id": assistant_msg.id})

    except BusinessError as e:
        # 业务异常以 error 事件告知前端（HTTP 状态仍是 200，因为流已建立）
        yield sse("error", {"code": e.code, "message": e.message})
    except Exception as e:
        logger.exception(f"对话处理异常 | kb={kb_id}")
        yield sse("error", {"code": ErrorCode.SERVER_ERROR, "message": "服务器内部错误，请稍后重试"})
    finally:
        db.close()
