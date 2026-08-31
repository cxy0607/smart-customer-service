"""安全模块：密码哈希（bcrypt）+ JWT 签发与校验

设计要点（面试可讲）：
- 密码绝不落库明文：bcrypt 自带随机盐，每次哈希结果不同，且计算慢（可抵御彩虹表与暴力破解）
- JWT 无状态认证：token 内自带用户身份与过期时间，服务端无需保存会话状态，水平扩展友好
- token 携带角色信息：接口权限校验无需每次查库；但用户被禁用等变更需重新登录才生效（token 有效期内不感知），
  本项目规模下这是可接受的权衡
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings
from app.core.exceptions import BusinessError, ErrorCode

settings = get_settings()


# ===== 密码 =====
def hash_password(password: str) -> str:
    """bcrypt 哈希（自动加随机盐）"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# ===== JWT =====
def create_access_token(user_id: int, username: str, role: str) -> str:
    """签发 token：payload 携带用户标识、角色与过期时间"""
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解析并校验 token，返回 payload；无效/过期抛出对应业务异常"""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise BusinessError(ErrorCode.TOKEN_EXPIRED, "登录已过期，请重新登录", http_status=401) from None
    except jwt.InvalidTokenError:
        raise BusinessError(ErrorCode.UNAUTHORIZED, "无效的登录凭证", http_status=401) from None
