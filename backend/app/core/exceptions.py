"""统一异常处理模块

设计思路（设计说明）：
- 业务代码只需抛出 BusinessError，由全局异常处理器统一转换为统一格式的 JSON 响应
- 前端只需处理一种响应结构，错误码与错误信息集中定义，便于维护
- 未预期的异常统一兜底返回 500，并记录完整堆栈日志（不向客户端泄露内部细节）

统一响应结构：
    {"code": 0, "message": "ok", "data": {...}}
    code = 0 表示成功；非 0 为业务错误码（与 HTTP 状态码对应，便于排查）
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import get_logger

logger = get_logger()


class BusinessError(Exception):
    """业务异常基类

    业务代码中主动抛出：raise BusinessError(40400, "知识库不存在")
    """

    def __init__(self, code: int, message: str, http_status: int = 200):
        self.code = code          # 业务错误码
        self.message = message    # 面向用户的错误描述
        self.http_status = http_status  # HTTP 状态码
        super().__init__(message)


# ===== 常用错误码定义（集中管理） =====
class ErrorCode:
    SUCCESS = 0
    PARAM_ERROR = 40000          # 参数错误
    UNAUTHORIZED = 40100         # 未登录 / token 无效
    TOKEN_EXPIRED = 40101        # token 过期
    FORBIDDEN = 40300            # 无权限
    NOT_FOUND = 40400            # 资源不存在
    RATE_LIMITED = 42900         # 触发限流
    SERVER_ERROR = 50000         # 服务器内部错误
    LLM_ERROR = 50001            # 大模型调用失败
    RAG_ERROR = 50002            # RAG 相关错误


def register_exception_handlers(app: FastAPI):
    """向 FastAPI 应用注册所有全局异常处理器"""

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        # 业务异常：正常返回业务错误码（记录 warn 日志便于排查高频错误）
        logger.warning(f"业务异常 | {request.method} {request.url.path} | code={exc.code} message={exc.message}")
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # 请求参数校验失败（FastAPI/Pydantic 自动触发）
        first_error = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(x) for x in first_error.get("loc", []) if x != "body")
        message = f"参数校验失败: {field} {first_error.get('msg', '')}"
        return JSONResponse(
            status_code=422,
            content={"code": ErrorCode.PARAM_ERROR, "message": message, "data": None},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        # 路由不存在(404)、方法不允许(405) 等框架级异常
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code * 100, "message": str(exc.detail), "data": None},
        )

    @app.exception_handler(Exception)
    async def unknown_error_handler(request: Request, exc: Exception):
        # 兜底：未预期异常，记录完整堆栈，对外只返回通用错误（不泄露内部细节）
        logger.exception(f"未预期异常 | {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={"code": ErrorCode.SERVER_ERROR, "message": "服务器内部错误，请稍后重试", "data": None},
        )
