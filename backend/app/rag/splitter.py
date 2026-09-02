"""文本切分模块：把长文档切成带重叠的语义片段

设计要点（设计说明）：
- 为什么要有 overlap（重叠）？纯按长度硬切会切断句子语义，
  相邻片段保留 50 字符重叠，保证跨片段边界的内容也能被完整检索到
- chunk_size 为什么是 500？片段是给向量模型和 LLM 用的：
  太大检索不精准、浪费上下文；太小语义不完整。500 字符对中文问答是经验均衡值
- 切分器支持中英文标点作为分隔符，优先在段落/句子边界切，而不是切在词中间
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 全局唯一切分器（无状态，进程内复用）
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,      # 每片最大字符数
    chunk_overlap=50,    # 相邻片段重叠字符数
    separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
    length_function=len,  # 按字符数计（中文场景比 token 计数更直观）
)


def split_documents(docs):
    """把 Document 列表切分为片段列表（metadata 自动继承）"""
    return text_splitter.split_documents(docs)
