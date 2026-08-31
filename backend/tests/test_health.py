"""健康检查接口测试"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """健康检查应返回 200 且包含组件状态"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "code" in body and "data" in body
    # 数据结构：包含 mysql/redis 两个组件的状态
    assert "mysql" in body["data"]["components"]
    assert "redis" in body["data"]["components"]
