"""FastAPI 依赖：认证与鉴权

使用方式（面试可讲）：
- 路由函数声明 user: User = Depends(get_current_user)，框架自动完成 token 解析与用户加载
- require_admin 基于 get_current_user 二次校验角色，实现 RBAC（角色访问控制）
"""
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, ErrorCode
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """解析 Authorization: Bearer <token>，返回当前登录用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise BusinessError(ErrorCode.UNAUTHORIZED, "未登录", http_status=401)
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise BusinessError(ErrorCode.UNAUTHORIZED, "用户不存在", http_status=401)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """管理员专属接口的依赖：非 admin 角色直接拒绝"""
    if user.role != "admin":
        raise BusinessError(ErrorCode.FORBIDDEN, "无权限，仅管理员可操作", http_status=403)
    return user
