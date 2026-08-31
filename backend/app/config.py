"""全局配置模块

使用 pydantic-settings 从 .env 文件读取配置，所有配置项集中在 Settings 类中。
.env 文件位于项目根目录（backend 的上一级），无论从哪个目录启动都能正确定位。
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录：backend/app/config.py -> 上两级 = project1/
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """应用配置，字段名与 .env 中的变量名一一对应"""

    # ===== 阿里云百炼大模型 =====
    DASHSCOPE_API_KEY: str = ""
    # 百炼 OpenAI 兼容接口地址
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # 对话模型：qwen-plus 效果与价格均衡；调试省钱可换 qwen-turbo
    LLM_MODEL: str = "qwen-plus"
    # 向量化模型
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ===== 数据库 =====
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "smart_cs"
    # 连接池大小与回收时间（防止 MySQL 8 小时断连问题）
    DB_POOL_SIZE: int = 10
    DB_POOL_RECYCLE: int = 3600

    # ===== Redis =====
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    # Redis 连接超时（秒），避免 Redis 故障时请求长时间挂起
    REDIS_SOCKET_TIMEOUT: float = 2.0

    # ===== JWT 认证 =====
    JWT_SECRET: str = ""
    # 加密算法
    JWT_ALGORITHM: str = "HS256"
    # token 有效期（分钟）
    JWT_EXPIRE_MINUTES: int = 720

    # ===== 文件与向量库 =====
    # 上传文件保存目录（相对项目根目录，实际落在 D 盘项目内）
    UPLOAD_DIR: str = "data/uploads"
    # Chroma 向量库持久化目录
    CHROMA_DIR: str = "data/chroma"

    # ===== 应用 =====
    APP_NAME: str = "智能客服问答系统"
    # 默认管理员账号（首次启动自动创建）
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # ===== 对话相关 =====
    # FAQ 向量匹配阈值（0~1），相似度超过该值视为命中 FAQ 直接回复
    FAQ_SIMILARITY_THRESHOLD: float = 0.85
    # 多轮对话携带的历史消息条数上限（控制 token 消耗）
    CHAT_HISTORY_LIMIT: int = 10
    # RAG 检索返回的文档片段数量
    RAG_TOP_K: int = 4
    # 限流：每用户每分钟对话请求上限
    RATE_LIMIT_CHAT_PER_MINUTE: int = 20

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def mysql_url(self) -> str:
        """拼接 SQLAlchemy 连接串（pymysql 驱动）"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    def resolve_path(self, relative: str) -> Path:
        """把配置中的相对目录解析为绝对路径（统一落到项目根目录下）"""
        path = Path(relative)
        return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（lru_cache 保证整个进程只加载一次 .env）"""
    return Settings()
