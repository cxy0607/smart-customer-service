"""Redis 滑动窗口限流

算法（关键技术点）：
- 用 Redis ZSET 实现：member 为"时间戳+随机数"（保证唯一），score 为请求时间戳
- 每次请求：删除窗口外的旧记录 -> 加入本次记录 -> 统计窗口内条数 -> 超限则拒绝
- 滑动窗口 vs 固定窗口：固定窗口在窗口边界（如 12:00:59 和 12:01:00 连续发）
  会瞬间放行 2 倍流量；滑动窗口任意时刻看最近 N 秒，流量更平滑，这是本项目的选择

降级策略（设计说明）：
- Redis 故障时不限流直接放行——限流是保护性功能，不能因为限流组件故障
  导致核心对话功能不可用（可用性优先，宁可放弃限流）
"""
import time
import uuid

from app.core.logger import get_logger
from app.db.redis_client import redis_available, redis_client

logger = get_logger()


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    """滑动窗口限流，返回 True 表示放行，False 表示触发限流

    :param key: 限流维度标识（如 chat:{user_id}）
    :param limit: 窗口内允许的最大请求数
    :param window_seconds: 窗口时长（秒）
    """
    if not redis_available():
        return True  # Redis 不可用：降级放行（保证核心功能可用）

    zkey = f"ratelimit:{key}"
    now = time.time()
    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(zkey, 0, now - window_seconds)  # 1. 移除窗口外记录
    pipe.zadd(zkey, {f"{now:.6f}:{uuid.uuid4().hex[:8]}": now})  # 2. 记录本次请求
    pipe.zcard(zkey)  # 3. 统计窗口内请求数
    pipe.expire(zkey, window_seconds)  # 4. 设置 key 过期，防止长期不用占用内存
    _, _, count, _ = pipe.execute()
    return count <= limit
