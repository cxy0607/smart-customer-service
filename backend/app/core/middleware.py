"""HTTP 中间件：请求 ID 全链路追踪

每个请求分配唯一 request_id（优先沿用客户端传入的 X-Request-ID，便于跨系统串联），
- 通过 loguru 上下文变量绑定到本次请求的所有日志
- 通过 X-Request-ID 响应头返回给前端，排查问题时前端报错可直接定位后端日志
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import get_logger

logger = get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 优先使用上游传入的请求 ID，否则生成一个
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        # 绑定到日志上下文：本次请求内所有日志自动携带该 ID
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
        # 响应头回传，前端可展示或上报
        response.headers["X-Request-ID"] = request_id
        return response
