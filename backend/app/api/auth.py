"""认证接口：登录、获取当前用户信息"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import BusinessError, ErrorCode
from app.core.response import ok
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", summary="登录获取 token")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    # 统一提示"用户名或密码错误"，不暴露账号是否存在（防撞库探测）
    if user is None or not verify_password(req.password, user.password_hash):
        raise BusinessError(ErrorCode.UNAUTHORIZED, "用户名或密码错误", http_status=401)

    token = create_access_token(user.id, user.username, user.role)
    return ok(TokenResponse(token=token, user=UserOut.model_validate(user)).model_dump())


@router.get("/me", summary="获取当前登录用户信息")
def me(user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(user).model_dump())
