"""知识库相关模型：知识库、文档、FAQ

文档处理状态机（面试可讲）：
    pending（已上传待处理）→ processing（解析/切分/向量化中）→ succeeded / failed
    - 上传接口只负责保存文件 + 落库(pending)，立即返回，不阻塞用户
    - 后台任务处理完成后更新状态；失败记录 error_msg，管理后台可点击"重试"
    - 状态机保证任何时刻可观测、可恢复，不会出现"卡在中间"的僵尸状态
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class KnowledgeBase(Base):
    """知识库：一个客服系统的知识域（如：售后政策库、产品手册库）"""

    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))  # 统一 UTC 存储，序列化时由 schemas/base.py 补时区


class Document(Base):
    """知识库中的文档：上传的 PDF/Word 文件及向量化处理状态"""

    __tablename__ = "documents"

    # 文档状态常量（状态机）
    STATUS_PENDING = "pending"        # 已上传，等待处理
    STATUS_PROCESSING = "processing"  # 正在解析/向量化
    STATUS_SUCCEEDED = "succeeded"    # 处理成功，可被检索
    STATUS_FAILED = "failed"          # 处理失败，可重试

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    # 原始文件名（展示用）
    filename: Mapped[str] = mapped_column(String(255))
    # 服务器上的存储路径
    stored_path: Mapped[str] = mapped_column(String(500))
    # 文件大小（字节）
    size: Mapped[int] = mapped_column(Integer, default=0)
    # 处理状态（状态机）
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    # 向量化后的片段数量
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # 失败原因（failed 状态时展示给管理员）
    error_msg: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))  # 统一 UTC 存储，序列化时由 schemas/base.py 补时区


class Faq(Base):
    """常见问题（FAQ）：预设的标准问答对，命中后直接返回，不走大模型"""

    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))  # 统一 UTC 存储，序列化时由 schemas/base.py 补时区
