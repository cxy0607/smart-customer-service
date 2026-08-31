"""大模型封装层：阿里云百炼（OpenAI 兼容接口）

设计思路（面试可讲）：
1. 为什么用 OpenAI 兼容接口而不是百炼原生 SDK？
   - 百炼提供 /compatible-mode/v1 兼容端点，langchain-openai 的 ChatOpenAI 可直接指向它
   - 代码与厂商解耦：将来换 DeepSeek / Kimi / OpenAI，只需改 .env 里的 base_url 和模型名，业务代码零改动
2. 为什么用单例？
   - LLM 客户端初始化涉及网络配置与资源，进程内复用一份即可，避免每次请求重复创建
3. 流式输出：streaming=True，后续对话接口用 SSE 把 token 逐字推给前端
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.core.exceptions import BusinessError, ErrorCode
from app.core.logger import get_logger
from app.llm.embeddings import BailianEmbeddings

logger = get_logger()

settings = get_settings()

# ===== 单例缓存 =====
_chat_model: BaseChatModel | None = None
_embedding_model: BailianEmbeddings | None = None


def _check_api_key():
    """启动时校验 API key 是否已配置，缺失时给出明确提示"""
    if not settings.DASHSCOPE_API_KEY:
        raise BusinessError(ErrorCode.LLM_ERROR, "未配置 DASHSCOPE_API_KEY，请在项目根目录 .env 中填写")


def get_chat_model() -> BaseChatModel:
    """获取对话模型单例（qwen-plus，流式输出）"""
    global _chat_model
    if _chat_model is None:
        _check_api_key()
        _chat_model = ChatOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,   # 百炼 OpenAI 兼容端点
            model=settings.LLM_MODEL,
            temperature=0.3,   # 客服场景需稳定可控，温度调低
            streaming=True,    # 开启流式，供 SSE 逐字推送
            timeout=60,
            max_retries=2,
        )
        logger.info(f"对话模型初始化完成: {settings.LLM_MODEL}")
    return _chat_model


def get_embedding_model() -> BailianEmbeddings:
    """获取向量化模型单例（text-embedding-v3，自定义封装适配百炼接口规范）"""
    global _embedding_model
    if _embedding_model is None:
        _check_api_key()
        _embedding_model = BailianEmbeddings(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            model=settings.EMBEDDING_MODEL,
        )
        logger.info(f"向量化模型初始化完成: {settings.EMBEDDING_MODEL}")
    return _embedding_model
