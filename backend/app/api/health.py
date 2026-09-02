"""健康检查接口

用途（设计说明）：
- Docker/K8s 健康探针：容器编排靠它判断服务是否存活、决定是否重启或摘流量
- 同时检查依赖组件（MySQL/Redis），运维可快速定位是应用挂了还是依赖挂了
"""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.exceptions import ErrorCode
from app.db.redis_client import redis_available
from app.db.session import engine

router = APIRouter(tags=["健康检查"])


@router.get("/health")
def health_check():
    """检查服务及各依赖组件状态，任一依赖异常返回 503（便于编排系统感知）"""
    components = {}

    # 检查 MySQL：执行 SELECT 1
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        components["mysql"] = "ok"
    except Exception:
        components["mysql"] = "error"

    # 检查 Redis：PING
    components["redis"] = "ok" if redis_available() else "error"

    all_ok = all(v == "ok" for v in components.values())
    return {
        "code": ErrorCode.SUCCESS if all_ok else 50001,
        "message": "服务正常" if all_ok else "依赖组件异常",
        "data": {"status": "healthy" if all_ok else "degraded", "components": components},
    }
