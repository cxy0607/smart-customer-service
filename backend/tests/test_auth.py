"""认证接口测试"""
import uuid

import pytest

from app.core.exceptions import ErrorCode
from app.db.redis_client import redis_client


@pytest.fixture(autouse=True)
def _clear_register_rate_limit():
    """每个测试前清掉注册接口的限流计数

    注册限流按来源 IP 计数，TestClient 所有测试共用同一个 IP，
    跨测试/跨运行会在 Redis 里累积误触限流，导致结果不确定。清掉保证测试独立可重复。
    """
    try:
        for key in redis_client.scan_iter("ratelimit:register:*"):
            redis_client.delete(key)
    except Exception:
        pass  # Redis 不可用时限流自动降级放行，测试照常执行
    yield


def test_login_success(client):
    """正确账号密码应返回 token 与用户信息"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["token"]
    assert body["data"]["user"]["role"] == "admin"


def test_login_wrong_password(client):
    """错误密码应返回 401 与统一错误码"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == ErrorCode.UNAUTHORIZED


def test_me_without_token(client):
    """未携带 token 访问受保护接口应 401"""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, auth_headers):
    """携带 token 应返回当前用户信息"""
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "admin"


# ===== 注册功能 =====

def _register_user(client, username):
    """注册一个普通用户并返回响应（用户名带随机后缀，测试间互不冲突）"""
    return client.post(
        "/api/v1/auth/register",
        json={"username": f"{username}_{uuid.uuid4().hex[:6]}", "password": "test123456"},
    )


def test_register_success(client):
    """注册成功应返回 token，且角色强制为 user（不允许注册成管理员）"""
    resp = _register_user(client, "newuser")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["token"]
    assert body["data"]["user"]["role"] == "user"  # 角色服务端硬编码，防越权


def test_register_duplicate_username(client):
    """重复用户名应被明确拒绝"""
    # 显式构造同一个用户名请求两次（不用 _register_user 的随机后缀，避免名字不一致）
    payload = {"username": f"dup_{uuid.uuid4().hex[:6]}", "password": "test123456"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "已被注册" in resp.json()["message"]


def test_register_weak_password(client):
    """密码少于 6 位应被 Pydantic 校验拒绝（422）"""
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": f"weak_{uuid.uuid4().hex[:6]}", "password": "12345"},
    )
    assert resp.status_code == 422


def test_register_password_over_bcrypt_limit(client):
    """密码超过 72 字节应被校验拒绝（bcrypt 上限，超长哈希会抛异常导致 500）"""
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": f"long_{uuid.uuid4().hex[:6]}", "password": "x" * 73},
    )
    assert resp.status_code == 422


def test_register_illegal_username(client):
    """用户名含特殊字符/中文/过短时应被校验拒绝（白名单字符规则）"""
    for bad in ["ab", "有中文", "has space", "bad-name!", "x" * 21]:
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": bad, "password": "test123456"},
        )
        assert resp.status_code == 422, f"用户名 {bad!r} 应被拒绝"


def test_register_then_login_and_rbac(client):
    """注册的用户可正常登录，但访问管理员接口应被 RBAC 拒绝（403）"""
    resp = _register_user(client, "rbacuser")
    token = resp.json()["data"]["token"]

    # 用注册时的密码能正常登录
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": resp.json()["data"]["user"]["username"], "password": "test123456"},
    )
    assert login_resp.status_code == 200

    # 普通用户访问管理员接口（如知识库创建）应 403
    kb_resp = client.post(
        "/api/v1/knowledge-bases",
        json={"name": f"越权测试_{uuid.uuid4().hex[:6]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert kb_resp.status_code == 403


def test_register_rate_limit(client):
    """同一 IP 60 秒内注册超过 5 次应触发限流（第 6 次 429）"""
    from app.db.redis_client import redis_available

    if not redis_available():
        pytest.skip("需要 Redis 才能验证限流（当前不可用，限流降级放行）")
    for _ in range(5):
        assert _register_user(client, "spam").status_code == 200
    resp = _register_user(client, "spam")
    assert resp.status_code == 429
    assert resp.json()["code"] == ErrorCode.RATE_LIMITED
