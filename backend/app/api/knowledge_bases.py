"""知识库管理接口

权限设计（RBAC，面试可讲）：
- 查看列表：所有登录用户（访客提问时需要选择知识库）
- 创建/修改/删除：仅管理员（知识库是运营资源，普通用户无权变更）
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user, require_admin
from app.core.exceptions import BusinessError, ErrorCode
from app.core.logger import get_logger
from app.core.response import ok
from app.db.session import get_db
from app.models.kb import Document, Faq, KnowledgeBase
from app.models.user import User
from app.rag.vectorstore import delete_collection, faq_collection_name
from app.schemas.kb import KnowledgeBaseCreate, KnowledgeBaseOut, KnowledgeBaseUpdate

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])
logger = get_logger()


@router.get("", summary="知识库列表（含文档数与 FAQ 数统计）")
def list_knowledge_bases(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kbs = db.query(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).all()
    # 统计每个知识库的文档数/FAQ数（子查询聚合，避免 N+1 查询）
    doc_counts = dict(
        db.query(Document.kb_id, func.count(Document.id)).group_by(Document.kb_id).all()
    )
    faq_counts = dict(
        db.query(Faq.kb_id, func.count(Faq.id)).group_by(Faq.kb_id).all()
    )
    data = [
        KnowledgeBaseOut.model_validate(kb).model_dump()
        | {"document_count": doc_counts.get(kb.id, 0), "faq_count": faq_counts.get(kb.id, 0)}
        for kb in kbs
    ]
    return ok(data)


@router.post("", summary="创建知识库（管理员）")
def create_knowledge_base(
    req: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.query(KnowledgeBase).filter(KnowledgeBase.name == req.name).first():
        raise BusinessError(ErrorCode.PARAM_ERROR, "知识库名称已存在")
    kb = KnowledgeBase(name=req.name, description=req.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    logger.info(f"知识库已创建 | id={kb.id} name={kb.name} by={admin.username}")
    return ok(KnowledgeBaseOut.model_validate(kb).model_dump())


@router.put("/{kb_id}", summary="修改知识库（管理员）")
def update_knowledge_base(
    kb_id: int,
    req: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")
    if req.name is not None:
        exists = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.name == req.name, KnowledgeBase.id != kb_id)
            .first()
        )
        if exists:
            raise BusinessError(ErrorCode.PARAM_ERROR, "知识库名称已存在")
        kb.name = req.name
    if req.description is not None:
        kb.description = req.description
    db.commit()
    db.refresh(kb)
    return ok(KnowledgeBaseOut.model_validate(kb).model_dump())


@router.delete("/{kb_id}", summary="删除知识库（管理员，级联清理）")
def delete_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """删除知识库：数据库记录（级联）+ 磁盘文件 + 向量数据（两个 collection）"""
    import shutil

    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")

    # 1. 清理向量：文档 collection + FAQ collection（collection 可能不存在，失败不阻塞删除）
    try:
        delete_collection(kb_id)
    except Exception as e:
        logger.warning(f"知识库向量清理异常 | kb={kb_id} error={e}")
    try:
        from app.rag.vectorstore import Chroma
        from app.llm.factory import get_embedding_model

        faq_store = Chroma(
            collection_name=faq_collection_name(kb_id),
            embedding_function=get_embedding_model(),
            persist_directory=str(get_settings().resolve_path(get_settings().CHROMA_DIR)),
        )
        faq_store.delete_collection()
    except Exception:
        pass  # 未创建过 FAQ 的知识库没有该 collection，忽略

    # 2. 清理上传文件目录
    upload_kb_dir = get_settings().resolve_path(get_settings().UPLOAD_DIR) / str(kb_id)
    shutil.rmtree(upload_kb_dir, ignore_errors=True)

    # 3. 删除数据库记录（外键 ondelete=CASCADE 级联删文档/FAQ）
    db.delete(kb)
    db.commit()
    logger.info(f"知识库已删除 | id={kb_id} by={admin.username}")
    return ok(message="知识库已删除")
