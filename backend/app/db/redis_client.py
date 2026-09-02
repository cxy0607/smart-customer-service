"""Redis 客户端模块

设计要点（设计说明）：
- 全局连接池：redis-py 自带连接池，避免每次操作都新建 TCP 连接
- socket_timeout 设短超时：Redis 故障时快速失败而不是无限挂起
- 业务层做降级：Redis 不可用时限流功能放行、缓存功能跳过，不影响核心对话功能
"""
import redis

from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger()

_settings = get_settings()

# 全局连接池（进程内共享）
_pool = redis.ConnectionPool(
    host=_settings.REDIS_HOST,
    port=_settings.REDIS_PORT,
    db=_settings.REDIS_DB,
    socket_timeout=_settings.REDIS_SOCKET_TIMEOUT,
    socket_connect_timeout=_settings.REDIS_SOCKET_TIMEOUT,
    decode_responses=True,  # 返回 str 而不是 bytes，业务代码更简洁
)

# 全局客户端实例
redis_client = redis.Redis(connection_pool=_pool)


def redis_available() -> bool:
    """检查 Redis 是否可用（健康检查与限流降级判断用）"""
    try:
        return bool(redis_client.ping())
    except Exception:
        logger.warning("Redis 连接不可用")
        return False
