"""认证相关模型"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import UTCDateTimeModel


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50, description="用户名")
    # 上限 72：bcrypt 只取前 72 字节，超长密码哈希会抛异常；登录场景同样限制，语义一致
    password: str = Field(min_length=1, max_length=72, description="密码")


class RegisterRequest(BaseModel):
    """注册请求：仅允许注册普通用户（角色由服务端强制指定，防越权注册管理员）"""

    # 用户名规则：3-20 位字母/数字/下划线（白名单字符，避免特殊字符引发展示或注入问题）
    username: str = Field(
        min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$", description="用户名（3-20位字母数字下划线）"
    )
    # 上限 72：bcrypt 只取前 72 字节，超长密码哈希会抛异常（质量门禁审查发现的隐患）
    password: str = Field(min_length=6, max_length=72, description="密码（6-72位）")


class UserOut(UTCDateTimeModel):
    """用户信息输出（不含密码哈希等敏感字段）"""

    id: int
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    token: str
    user: UserOut
