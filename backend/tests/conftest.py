"""pytest 公共 fixture

说明：测试使用本机真实 MySQL/Redis（开发环境已就绪），
每次测试会话通过 lifespan 自动建表与初始化默认管理员（幂等操作）
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    """带 lifespan 的测试客户端：自动完成建表与管理员初始化"""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client) -> str:
    """登录默认管理员，返回 Bearer token"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, f"管理员登录失败: {resp.text}"
    return resp.json()["data"]["token"]


@pytest.fixture()
def auth_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
