"""FastAPI 应用入口

采用应用工厂模式（面试可讲）：
- create_app() 返回应用实例，便于测试时创建隔离实例、未来扩展多环境配置
- 中间件、异常处理器、路由注册集中在工厂函数中，一目了然
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import get_logger
from app.core.middleware import RequestIDMiddleware

logger = get_logger()
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/api/docs",        # Swagger 文档地址
        openapi_url="/api/openapi.json",
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

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    # 直接运行本文件时启动开发服务器
    # 正式启动命令：uvicorn app.main:app --host 0.0.0.0 --port 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
