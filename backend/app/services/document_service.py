"""文档业务逻辑：上传保存 + 异步向量化处理（状态机流转）

异步处理方案（面试可讲）：
- 大文档的解析 + 向量化要调用 embedding API，耗时可达几十秒，
  若同步处理会长时间占用 HTTP 连接，用户体验差且易超时
- 本项目用 FastAPI BackgroundTasks 做轻量异步：上传接口立即返回(pending)，
  后台任务处理完更新状态
- 演进方向：真实企业环境会把任务投递到 Celery/RabbitMQ 队列由独立 worker 消费，
  本项目的处理函数设计成"幂等、可重试"，迁移到队列时逻辑无需改动
- 兜底：进程重启可能中断后台任务，此时文档停留在 pending/processing，
  管理后台提供「重试」按钮人工恢复
"""
import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import BusinessError, ErrorCode
from app.core.logger import get_logger
from app.models.kb import Document, KnowledgeBase
from app.rag.loader import SUPPORTED_EXTENSIONS, load_document
from app.rag.splitter import split_documents
from app.rag.vectorstore import add_documents

logger = get_logger()
settings = get_settings()

# 上传大小上限：20MB
MAX_UPLOAD_SIZE = 20 * 1024 * 1024


def save_upload(db: Session, kb_id: int, filename: str, file_obj) -> Document:
    """保存上传文件 + 创建 pending 状态的文档记录

    注意：本函数不负责向量化，调用方需随后用 BackgroundTasks 触发 process_document
    """
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")

    # 校验文件类型（白名单，防止上传可执行文件等）
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise BusinessError(ErrorCode.PARAM_ERROR, f"不支持的文件类型 {ext}，仅支持 PDF / Word")

    # 保存到 data/uploads/{kb_id}/{uuid}_{filename}（项目目录内，D 盘）
    upload_dir = settings.resolve_path(settings.UPLOAD_DIR) / str(kb_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:12]}_{filename}"
    stored_path = upload_dir / stored_name

    size = 0
    with open(stored_path, "wb") as f:
        while chunk := file_obj.read(1024 * 1024):  # 分块写入，避免大文件占满内存
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE:
                f.close()
                stored_path.unlink(missing_ok=True)
                raise BusinessError(ErrorCode.PARAM_ERROR, "文件超过 20MB 上限")
            f.write(chunk)

    doc = Document(
        kb_id=kb_id,
        filename=filename,
        stored_path=str(stored_path),
        size=size,
        status=Document.STATUS_PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info(f"文档已上传待处理 | id={doc.id} kb={kb_id} filename={filename} size={size}")
    return doc


def process_document(doc_id: int) -> None:
    """后台任务：解析 -> 切分 -> 向量化 -> 更新状态

    幂等设计：任何一步失败都会把状态置为 failed 并记录原因，可安全重试
    """
    # 独立数据库会话（后台任务与请求生命周期不同，不能复用请求的 Session）
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            logger.warning(f"后台任务找不到文档 | id={doc_id}")
            return

        # 状态流转：pending/processing -> processing
        doc.status = Document.STATUS_PROCESSING
        db.commit()

        # 1. 解析文件
        loaded = load_document(Path(doc.stored_path))
        if not loaded:
            raise BusinessError(ErrorCode.RAG_ERROR, "文档中未提取到文本内容（可能为扫描件）")
        # 统一 metadata.source 为原始文件名：
        # 磁盘文件名为 uuid 前缀 + 原始名（防重名），但引用展示与删除匹配都用原始名
        for d in loaded:
            d.metadata["source"] = doc.filename

        # 2. 语义切分
        chunks = split_documents(loaded)

        # 3. 向量化写入（调用百炼 embedding API，耗时主要在此）
        add_documents(doc.kb_id, chunks)

        # 4. 成功：更新状态与片段数
        doc.status = Document.STATUS_SUCCEEDED
        doc.chunk_count = len(chunks)
        doc.error_msg = ""
        db.commit()
        logger.info(f"文档向量化完成 | id={doc_id} chunks={len(chunks)}")

    except Exception as e:
        # 失败：状态置 failed，记录原因（业务异常取 message，未知异常取类型名）
        db.rollback()
        doc = db.get(Document, doc_id)
        if doc is not None:
            doc.status = Document.STATUS_FAILED
            doc.error_msg = str(getattr(e, "message", e))[:500]
            db.commit()
        logger.error(f"文档向量化失败 | id={doc_id} error={e}")
    finally:
        db.close()


def delete_document(db: Session, doc_id: int) -> None:
    """删除文档：数据库记录 + 磁盘文件 + 向量数据 三处同步清理"""
    from app.rag.vectorstore import delete_documents

    doc = db.get(Document, doc_id)
    if doc is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "文档不存在")

    kb_id = doc.kb_id
    filename = doc.filename  # 原始文件名：与向量 metadata.source 一致（见 process_document）
    stored_path = doc.stored_path

    # 清理向量（仅 succeeded 状态的文档有向量）
    if doc.status == Document.STATUS_SUCCEEDED:
        delete_documents(kb_id, filename)

    # 清理磁盘文件
    Path(stored_path).unlink(missing_ok=True)

    # 删除记录
    db.delete(doc)
    db.commit()
    logger.info(f"文档已删除 | id={doc_id} kb={kb_id}")


def retry_document(db: Session, doc_id: int) -> Document:
    """重试失败的文档：状态重置为 pending，由调用方再次投递后台任务"""
    doc = db.get(Document, doc_id)
    if doc is None:
        raise BusinessError(ErrorCode.NOT_FOUND, "文档不存在")
    if doc.status == Document.STATUS_SUCCEEDED:
        raise BusinessError(ErrorCode.PARAM_ERROR, "文档已处理成功，无需重试")

    doc.status = Document.STATUS_PENDING
    doc.error_msg = ""
    db.commit()
    db.refresh(doc)
    logger.info(f"文档重试已排队 | id={doc_id}")
    return doc
