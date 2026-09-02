"""百炼向量化封装：自定义 LangChain Embeddings 实现

为什么要自定义而不直接用 langchain-openai 的 OpenAIEmbeddings（设计说明）：
- langchain-openai 的 OpenAIEmbeddings 在批量处理时用 tiktoken 把文本编码成 token 数组发给 API，
  而百炼兼容接口的 /embeddings 只接受字符串输入（报错 InvalidParameter: contents is neither str nor list of str）
- 自定义实现直接对接百炼规范：字符串列表 + 分批控制，行为完全可控
- 分批策略：text-embedding-v3 单次请求最多 10 条文本，超出的按批拆分，避免触发服务端限制
"""
from langchain_core.embeddings import Embeddings
from openai import OpenAI

from app.core.logger import get_logger

logger = get_logger()

# 百炼 text-embedding-v3 单次请求最大文本条数
BATCH_SIZE = 10


class BailianEmbeddings(Embeddings):
    """百炼向量模型（OpenAI 兼容接口），实现 LangChain Embeddings 协议"""

    def __init__(self, api_key: str, base_url: str, model: str):
        # 复用 openai SDK 的客户端（与 langchain-openai 底层一致）
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文档片段（自动分批）"""
        if not texts:
            return []
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = self._client.embeddings.create(
                model=self.model,
                input=batch,  # 百炼只接受字符串/字符串列表
            )
            # 服务端按 index 返回，排序后保证与输入顺序一致
            data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend(d.embedding for d in data)
            logger.debug(f"向量化进度: {i + len(batch)}/{len(texts)}")
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """向量化单条查询文本"""
        return self.embed_documents([text])[0]
