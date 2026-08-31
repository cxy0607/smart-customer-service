"""认证接口测试"""
from app.core.exceptions import ErrorCode


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
