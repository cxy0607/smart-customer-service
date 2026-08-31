"""文档管理接口：上传（异步向量化）、列表、删除、重试

流程（面试可讲）：
- 上传：保存文件 -> 落库(pending) -> 立即返回 -> BackgroundTasks 后台向量化
- 前端轮询/刷新列表查看状态变化：pending -> processing -> succeeded/failed
- 失败可重试：真实企业会由消息队列保证任务不丢失，本项目用 BackgroundTasks
  实现轻量版，重试机制兜底进程重启等场景
"""
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.exceptions import BusinessError, ErrorCode
from app.core.response import ok
from app.db.session import get_db
from app.models.kb import Document, KnowledgeBase
from app.models.user import User
from app.schemas.kb import DocumentOut
from app.services.document_service import (
    delete_document,
    process_document,
    retry_document,
    save_upload,
)

router = APIRouter(tags=["文档"])


@router.post("/knowledge-bases/{kb_id}/documents", summary="上传文档（管理员，后台自动向量化）")
def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF / Word 文件，≤20MB"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.get(KnowledgeBase, kb_id) is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")
    if not file.filename:
        raise BusinessError(ErrorCode.PARAM_ERROR, "文件名不能为空")

    # 保存文件 + 创建 pending 记录
    doc = save_upload(db, kb_id, file.filename, file.file)
    # 投递后台任务：响应返回后由 FastAPI 执行向量化
    background_tasks.add_task(process_document, doc.id)
    return ok(DocumentOut.model_validate(doc).model_dump(), message="上传成功，正在后台处理")


@router.get("/knowledge-bases/{kb_id}/documents", summary="知识库下的文档列表（管理员）")
def list_documents(
    kb_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.get(KnowledgeBase, kb_id) is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")
    docs = (
        db.query(Document)
        .filter(Document.kb_id == kb_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return ok([DocumentOut.model_validate(d).model_dump() for d in docs])


@router.delete("/documents/{doc_id}", summary="删除文档（管理员，同步清理文件与向量）")
def remove_document(
    doc_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    delete_document(db, doc_id)
    return ok(message="文档已删除")


@router.post("/documents/{doc_id}/retry", summary="重试失败的文档（管理员）")
def retry_failed_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    doc = retry_document(db, doc_id)
    background_tasks.add_task(process_document, doc.id)
    return ok(DocumentOut.model_validate(doc).model_dump(), message="已重新加入处理队列")
