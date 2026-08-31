"""向量存储模块：Chroma 持久化向量库

设计要点（面试可讲）：
- 为什么选 Chroma 而不是 Milvus / Qdrant？
  项目规模数据量在十万级片段以内，Chroma 嵌入式部署（与后端同进程）即可满足，
  无需额外服务与运维成本；且 LangChain 原生集成，开发效率高。
  若数据量增长到百万级，存储层做了抽象，可平滑迁移到 Milvus 等独立向量库。
- 每个知识库一个 collection（kb_{id}）：实现知识库之间的向量隔离，
  删除整个知识库时直接删 collection，不会残留数据
- persist_directory 持久化到项目 data/chroma 目录（D 盘），容器部署时挂载卷即可保留数据
"""
from langchain_chroma import Chroma

from app.config import get_settings
from app.core.logger import get_logger
from app.llm.factory import get_embedding_model

logger = get_logger()
settings = get_settings()


def collection_name(kb_id: int) -> str:
    """知识库 ID -> Chroma collection 名称"""
    return f"kb_{kb_id}"


def _get_store(kb_id: int) -> Chroma:
    """获取指定知识库的向量存储实例（每次按 collection 定位）"""
    return Chroma(
        collection_name=collection_name(kb_id),
        embedding_function=get_embedding_model(),
        persist_directory=str(settings.resolve_path(settings.CHROMA_DIR)),
        # 把余弦距离转换为相似度：返回值越接近 1 表示越相似，语义直观
        relevance_score_fn=lambda distance: 1.0 - distance,
    )


def add_documents(kb_id: int, docs: list) -> int:
    """把切分后的片段写入指定知识库，返回写入的片段数"""
    store = _get_store(kb_id)
    # Chroma 内部自动按 id 去重；为支持"同一文档重传"，用 source+内容 生成稳定 id
    store.add_documents(docs)
    return len(docs)


def delete_documents(kb_id: int, source: str) -> None:
    """删除指定知识库中来源于某文件的所有片段"""
    store = _get_store(kb_id)
    results = store.get(where={"source": source})
    if results and results["ids"]:
        store.delete(ids=results["ids"])
        logger.info(f"已删除向量片段 {len(results['ids'])} 条 | kb={kb_id} source={source}")


def delete_collection(kb_id: int) -> None:
    """删除整个知识库的向量数据"""
    store = _get_store(kb_id)
    store.delete_collection()
    logger.info(f"已删除知识库向量数据 | kb={kb_id}")


def search_with_score(kb_id: int, query: str, k: int = 4) -> list:
    """相似度检索：返回 [(Document, score)]，score 越接近 1 越相似（余弦相似度）"""
    store = _get_store(kb_id)
    return store.similarity_search_with_score(query, k=k)


# ===== FAQ 向量匹配（FAQ 优先策略的检索层） =====

def faq_collection_name(kb_id: int) -> str:
    """FAQ 问题的向量 collection：与文档 collection 分离，互不干扰"""
    return f"kb_{kb_id}_faq"


def upsert_faq_vector(kb_id: int, faq_id: int, question: str) -> None:
    """新增/更新 FAQ 时同步其问题向量（id 固定为 faq_{id}，天然支持覆盖更新）"""
    store = Chroma(
        collection_name=faq_collection_name(kb_id),
        embedding_function=get_embedding_model(),
        persist_directory=str(settings.resolve_path(settings.CHROMA_DIR)),
        relevance_score_fn=lambda distance: 1.0 - distance,
    )
    store.add_texts(texts=[question], ids=[f"faq_{faq_id}"], metadatas=[{"faq_id": faq_id}])


def delete_faq_vector(kb_id: int, faq_id: int) -> None:
    """删除 FAQ 时同步删除其向量"""
    store = Chroma(
        collection_name=faq_collection_name(kb_id),
        embedding_function=get_embedding_model(),
        persist_directory=str(settings.resolve_path(settings.CHROMA_DIR)),
        relevance_score_fn=lambda distance: 1.0 - distance,
    )
    store.delete(ids=[f"faq_{faq_id}"])


def match_faq(kb_id: int, query: str, threshold: float) -> tuple[int, float] | None:
    """把用户问题与 FAQ 问题做向量匹配

    返回 (faq_id, similarity)；低于阈值返回 None（视为未命中，交给 RAG 处理）
    """
    store = Chroma(
        collection_name=faq_collection_name(kb_id),
        embedding_function=get_embedding_model(),
        persist_directory=str(settings.resolve_path(settings.CHROMA_DIR)),
        relevance_score_fn=lambda distance: 1.0 - distance,
    )
    results = store.similarity_search_with_score(query, k=1)
    if not results:
        return None
    doc, similarity = results[0]
    if similarity < threshold:
        return None
    return doc.metadata["faq_id"], similarity
