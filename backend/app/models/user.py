"""用户模型"""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 登录名，唯一
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    # bcrypt 哈希后的密码，绝不明文存储
    password_hash: Mapped[str] = mapped_column(String(255))
    # 角色：admin（管理员，可管理知识库/FAQ/查看记录）/ user（访客，仅可提问）
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
