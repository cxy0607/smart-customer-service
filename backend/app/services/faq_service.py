"""FAQ 业务逻辑：数据库与向量索引的一致性维护

一致性策略（面试可讲）：
- FAQ 的「问题」需要向量化后才能被向量匹配命中，数据库记录与向量必须同步
- 采用「先向量、后落库」：向量写入成功才提交数据库事务；
  向量写失败则整个操作失败回滚，不会出现"库里有条 FAQ 但永远匹配不到"的不一致状态
"""
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, ErrorCode
from app.core.logger import get_logger
from app.models.kb import Faq, KnowledgeBase
from app.rag.vectorstore import delete_faq_vector, upsert_faq_vector

logger = get_logger()


def _check_kb(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")
    return kb


def create_faq(db: Session, kb_id: int, question: str, answer: str) -> Faq:
    """创建 FAQ：先写向量索引，再落库（向量失败则整体失败）"""
    _check_kb(db, kb_id)

    faq = Faq(kb_id=kb_id, question=question, answer=answer)
    db.add(faq)
    db.flush()  # 先拿到自增 id（向量索引需要）

    try:
        upsert_faq_vector(kb_id, faq.id, question)
    except Exception as e:
        db.rollback()
        logger.error(f"FAQ 向量写入失败 | kb={kb_id} error={e}")
        raise BusinessError(ErrorCode.RAG_ERROR, "FAQ 向量化失败，请稍后重试") from e

    db.commit()
    db.refresh(faq)
    logger.info(f"FAQ 已创建 | id={faq.id} kb={kb_id}")
    return faq


def update_faq(db: Session, faq_id: int, question: str | None, answer: str | None) -> Faq:
    """更新 FAQ：问题变化时同步更新向量索引"""
    faq = db.get(Faq, faq_id)
    if faq is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "FAQ 不存在")

    new_question = question if question is not None else faq.question
    new_answer = answer if answer is not None else faq.answer

    try:
        # 问题文本变化才需要更新向量（内容相同则跳过，节省一次 API 调用）
        if new_question != faq.question:
            upsert_faq_vector(faq.kb_id, faq.id, new_question)
    except Exception as e:
        db.rollback()
        logger.error(f"FAQ 向量更新失败 | id={faq_id} error={e}")
        raise BusinessError(ErrorCode.RAG_ERROR, "FAQ 向量化失败，请稍后重试") from e

    faq.question = new_question
    faq.answer = new_answer
    db.commit()
    db.refresh(faq)
    logger.info(f"FAQ 已更新 | id={faq_id}")
    return faq


def delete_faq(db: Session, faq_id: int) -> None:
    """删除 FAQ：同步删除向量索引与数据库记录"""
    faq = db.get(Faq, faq_id)
    if faq is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "FAQ 不存在")

    # 向量删除是本地操作（不调 API），失败概率极低；先删向量保证索引不残留
    delete_faq_vector(faq.kb_id, faq.id)
    db.delete(faq)
    db.commit()
    logger.info(f"FAQ 已删除 | id={faq_id}")
