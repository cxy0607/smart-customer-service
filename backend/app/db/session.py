"""数据库模块：SQLAlchemy 2.x 连接管理

设计要点（设计说明）：
- pool_pre_ping=True：每次取连接前先 ping，自动剔除 MySQL 断开（如 8 小时无操作超时）的死连接
- pool_recycle：连接定期回收，防止 MySQL 侧主动断开导致连接池里堆积失效连接
- Base 继承 DeclarativeBase，所有 ORM 模型统一继承，Alembic 迁移基于同一元数据
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

# 创建引擎：pymysql 驱动连接 MySQL
engine = create_engine(
    settings.mysql_url,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=20,
    echo=False,  # 调试时可改为 True 查看实际执行的 SQL
)

# 会话工厂：每个请求一个 Session（由 FastAPI 依赖注入创建与关闭）
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


def get_db():
    """FastAPI 依赖：请求开始时创建会话，请求结束时关闭（yield 保证异常时也能释放）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
