"""FAQ 管理接口（管理员）：增删改查，操作时同步维护向量索引"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.exceptions import BusinessError, ErrorCode
from app.core.response import ok
from app.db.session import get_db
from app.models.kb import Faq, KnowledgeBase
from app.models.user import User
from app.schemas.kb import FaqCreate, FaqOut, FaqUpdate
from app.services.faq_service import create_faq, delete_faq, update_faq

router = APIRouter(prefix="/faqs", tags=["FAQ"])


@router.get("/knowledge-bases/{kb_id}/faqs", summary="知识库下的 FAQ 列表（管理员）")
def list_faqs(
    kb_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.get(KnowledgeBase, kb_id) is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")
    faqs = db.query(Faq).filter(Faq.kb_id == kb_id).order_by(Faq.created_at.desc()).all()
    return ok([FaqOut.model_validate(f).model_dump() for f in faqs])


@router.post("/knowledge-bases/{kb_id}/faqs", summary="创建 FAQ（管理员）")
def add_faq(
    kb_id: int,
    req: FaqCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    faq = create_faq(db, kb_id, req.question, req.answer)
    return ok(FaqOut.model_validate(faq).model_dump(), message="FAQ 已创建")


@router.put("/{faq_id}", summary="修改 FAQ（管理员）")
def edit_faq(
    faq_id: int,
    req: FaqUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    faq = update_faq(db, faq_id, req.question, req.answer)
    return ok(FaqOut.model_validate(faq).model_dump(), message="FAQ 已更新")


@router.delete("/{faq_id}", summary="删除 FAQ（管理员）")
def remove_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    delete_faq(db, faq_id)
    return ok(message="FAQ 已删除")
