"""认证接口：注册、登录、获取当前用户信息"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import BusinessError, ErrorCode
from app.core.rate_limit import check_rate_limit
from app.core.response import ok
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", summary="注册普通用户（注册即登录）")
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    # 防批量注册：按来源 IP 限流（注册是匿名接口，无用户身份，只能按 IP 维度）
    # Redis 故障时限流降级放行，不影响注册功能（与对话接口同一策略）
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"register:{client_ip}", 5, 60):
        raise BusinessError(ErrorCode.RATE_LIMITED, "注册过于频繁，请稍后再试", http_status=429)

    if db.query(User).filter(User.username == req.username).first():
        # 注册场景必须明确提示"已被注册"，与登录接口的模糊提示不同（登录防撞库，注册要告知用户）
        # 显式传 http_status=400：请求本身有错（名字被占），语义上不是成功响应
        raise BusinessError(ErrorCode.PARAM_ERROR, "该用户名已被注册", http_status=400)

    # 角色在服务端硬编码为 user（不接受客户端传入角色，防止越权注册管理员——面试重点）
    user = User(username=req.username, password_hash=hash_password(req.password), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    # 注册即登录：直接返回 token，省去用户注册后再登录一步
    token = create_access_token(user.id, user.username, user.role)
    return ok(TokenResponse(token=token, user=UserOut.model_validate(user)).model_dump())


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
