"""日志模块

使用 loguru 实现结构化日志：
- 控制台输出（开发调试）+ 文件输出（按天轮转、自动清理，供线上排查）
- 支持通过上下文变量携带 request_id，实现单次请求的日志串联（全链路追踪）
"""
import sys
from pathlib import Path

from loguru import logger

from app.config import get_settings

# 日志目录：项目根目录 logs/（D 盘），目录不存在则自动创建
LOG_DIR = get_settings().resolve_path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 移除默认 handler，按需重新配置
logger.remove()

# 为 request_id 提供默认值：非 HTTP 环境（脚本/后台任务）未绑定时显示 "-"
logger.configure(extra={"request_id": "-"})

# 控制台：开发时便于观察，带颜色
logger.add(
    sys.stdout,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[request_id]}</cyan> | "
        "<level>{message}</level>"
    ),
)

# 文件：按天轮转，保留 14 天，压缩历史日志节省磁盘
logger.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",
    level="INFO",
    rotation="00:00",
    retention="14 days",
    compression="zip",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[request_id]} | {name}:{function}:{line} - {message}",
)


def get_logger():
    """获取全局 logger（供各模块引用）"""
    return logger
