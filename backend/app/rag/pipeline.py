"""RAG 生成流水线：检索 → 组织上下文 → 流式生成

设计要点（面试可讲）：
- 防幻觉策略：系统提示词强制要求「只根据知识库内容回答，没有就明说不知道」，
  这是客服场景的第一原则——宁可说不知道，也不能编造产品信息误导客户
- 来源引用：检索到的片段连同文件名、页码一起返回给前端展示，
  用户可点击来源验证答案，同时满足合规审计需求
- 历史窗口：多轮对话只携带最近 N 条历史（CHAT_HISTORY_LIMIT），
  控制 token 消耗，防止对话变长后请求成本线性增长
"""
from typing import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import get_settings
from app.core.exceptions import BusinessError, ErrorCode
from app.core.logger import get_logger
from app.llm.factory import get_chat_model
from app.rag.vectorstore import search_with_score

logger = get_logger()
settings = get_settings()

# 系统提示词：定义客服角色与核心约束（防幻觉是第一原则）
SYSTEM_PROMPT = f"""你是{settings.APP_NAME}的智能客服助手，请严格遵守以下规则：
1. 只根据提供的「知识库内容」回答用户问题；如果知识库内容中没有相关信息，
   直接回答"抱歉，知识库中暂无相关内容，建议联系人工客服。"，严禁编造答案。
2. 回答使用中文，简洁、准确、条理清晰。
3. 用户进行问候、感谢等礼貌性对话时，可正常回应，不需要引用知识库。"""


def _build_context(docs: list) -> str:
    """把检索到的片段拼接为上下文文本（带来源标注）"""
    parts = []
    for i, (doc, score) in enumerate(docs, start=1):
        source = doc.metadata.get("source", "未知来源")
        page = doc.metadata.get("page", "")
        page_label = f" 第{page}页" if page else ""
        parts.append(f"[片段{i} | 来源: {source}{page_label}]\n{doc.page_content}")
    return "\n\n".join(parts)


def retrieve(kb_id: int, query: str, top_k: int | None = None) -> list:
    """检索知识库：返回 [(Document, similarity)]，相似度从高到低"""
    top_k = top_k or settings.RAG_TOP_K
    try:
        docs = search_with_score(kb_id, query, k=top_k)
    except Exception as e:
        logger.error(f"向量检索失败 | kb={kb_id} | error={e}")
        raise BusinessError(ErrorCode.RAG_ERROR, "知识库检索失败，请稍后重试") from e
    return docs


def build_messages(query: str, context_docs: list, history: list[dict]) -> list:
    """组装发送给 LLM 的消息列表：系统提示 + 历史对话 + 带上下文的问题"""
    # 历史只取最近 N 条，且只保留 user/assistant 两类消息
    recent = [m for m in history if m["role"] in ("user", "assistant")][-settings.CHAT_HISTORY_LIMIT:]

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in recent:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))

    if context_docs:
        # 有检索结果：把上下文拼进问题（RAG 的核心注入方式）
        context = _build_context(context_docs)
        messages.append(
            HumanMessage(content=f"知识库内容：\n{context}\n\n用户问题：{query}")
        )
    else:
        messages.append(HumanMessage(content=query))
    return messages


def stream_generate(query: str, context_docs: list, history: list[dict]) -> Iterator[str]:
    """流式生成回答，逐段产出文本（供 SSE 逐字推送）"""
    messages = build_messages(query, context_docs, history)
    model = get_chat_model()
    try:
        for chunk in model.stream(messages):
            # LangChain 1.x：chunk 为 AIMessageChunk，content 可能为 list
            text = chunk.content
            if isinstance(text, list):
                text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
            if text:
                yield text
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"LLM 调用失败 | error={e}")
        raise BusinessError(ErrorCode.LLM_ERROR, "大模型服务暂时不可用，请稍后重试") from e
