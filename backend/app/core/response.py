"""统一响应格式工具

所有接口返回 {"code": 0, "message": "ok", "data": ...}，
前端只需处理一种结构（见 core/exceptions.py 中的错误码约定）
"""
from app.core.exceptions import ErrorCode


def ok(data=None, message: str = "ok") -> dict:
    """成功响应"""
    return {"code": ErrorCode.SUCCESS, "message": message, "data": data}
