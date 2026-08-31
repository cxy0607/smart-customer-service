"""FastAPI 应用入口

采用应用工厂模式（面试可讲）：
- create_app() 返回应用实例，便于测试时创建隔离实例、未来扩展多环境配置
- 中间件、异常处理器、路由注册集中在工厂函数中，一目了然
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, chat, documents, faqs, health, knowledge_bases
from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import get_logger
from app.core.middleware import RequestIDMiddleware

logger = get_logger()
settings = get_settings()


def _init_database():
    """启动时初始化：建表（开发期便捷方案，正式环境用 Alembic 迁移）+ 默认管理员账号

    说明（面试可讲）：生产环境的表结构变更应使用 Alembic 迁移脚本管理，
    此处 create_all 仅保证开发/首启即用；本项目阶段 6 已接入 Alembic 迁移。
    """
    from app.db.session import Base, SessionLocal, engine
    from app import models  # noqa: F401  确保所有模型已注册到 metadata
    from app.core.security import hash_password
    from app.models.user import User

    Base.metadata.create_all(bind=engine)

    # 首次启动自动创建默认管理员（账号密码见 .env，可修改）
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == settings.ADMIN_USERNAME).first() is None:
            admin = User(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            db.commit()
            logger.info(f"默认管理员已创建: {settings.ADMIN_USERNAME}（请尽快修改密码）")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理资源"""
    logger.info(f"{settings.APP_NAME} 启动中...")
    _init_database()
    logger.info("启动完成，接口文档: /api/docs")
    yield
    logger.info("应用关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/api/docs",        # Swagger 文档地址
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # 1. 中间件（先注册的先执行，顺序敏感）
    # CORS：允许 Vue3 开发服务器（5173 端口）跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # 请求 ID 追踪
    app.add_middleware(RequestIDMiddleware)

    # 2. 全局异常处理器
    register_exception_handlers(app)

    # 3. 路由注册（统一前缀 /api/v1）
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(knowledge_bases.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(faqs.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    # 直接运行本文件时启动开发服务器
    # 正式启动命令：uvicorn app.main:app --host 0.0.0.0 --port 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
