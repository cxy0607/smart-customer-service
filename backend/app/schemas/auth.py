"""认证相关模型"""
from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50, description="用户名")
    password: str = Field(min_length=1, max_length=100, description="密码")


class UserOut(BaseModel):
    """用户信息输出（不含密码哈希等敏感字段）"""

    id: int
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    token: str
    user: UserOut
