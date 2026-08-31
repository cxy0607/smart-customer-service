"""RAG 流水线验证脚本（开发调试用，不参与生产运行）

走通全流程：生成测试文档 -> 加载 -> 切分 -> 向量化 -> 检索 -> 流式生成
运行方式（backend 目录下）：
    .venv/Scripts/python -m scripts.rag_demo
"""
import sys
from pathlib import Path

# 保证从 backend 目录运行时可导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import docx

from app.core.logger import get_logger
from app.rag.loader import load_document
from app.rag.pipeline import retrieve, stream_generate
from app.rag.splitter import split_documents
from app.rag.vectorstore import add_documents, delete_collection

logger = get_logger()

TEST_KB_ID = 999  # 测试用知识库 id，用后即删

# 测试文档内容：模拟某电商公司的售后知识
TEST_CONTENT = """云商城售后服务说明

一、退换货政策
用户自签收商品之日起 7 天内，商品保持完好且不影响二次销售，可申请无理由退货。
退货物流费用由用户承担；若因商品质量问题退货，运费由商城承担。
换货政策：商品存在质量问题，15 天内可申请免费换货。

二、退款时效
退货商品经仓库验收通过后，退款将在 1-3 个工作日内原路退回支付账户。
信用卡支付退款到账时间以银行处理为准，一般 3-7 个工作日。

三、发票说明
商城所有商品均支持开具电子发票，下单时在订单页勾选"需要发票"即可。
发票抬头支持个人和公司，公司抬头需填写税号。

四、物流配送
默认使用顺丰速运，全国大部分地区 1-3 天送达。
偏远地区（新疆、西藏等）配送时效为 5-7 天。
"""


def make_test_docx() -> Path:
    """生成测试用 Word 文档"""
    path = Path(__file__).resolve().parents[1] / "data" / "test_docs" / "售后政策.docx"
    path.parent.mkdir(parents=True, exist_ok=True)
    document = docx.Document()
    for paragraph in TEST_CONTENT.split("\n"):
        if paragraph.strip():
            document.add_paragraph(paragraph.strip())
    document.save(str(path))
    return path


def main():
    print("=" * 60)
    print("第 1 步：生成测试文档（Word）")
    docx_path = make_test_docx()
    print(f"  -> {docx_path}")

    print("第 2 步：加载文档")
    docs = load_document(docx_path)
    print(f"  -> 解析出 {len(docs)} 个 Document")

    print("第 3 步：文本切分")
    chunks = split_documents(docs)
    print(f"  -> 切分为 {len(chunks)} 个片段（chunk_size=500, overlap=50）")
    for i, c in enumerate(chunks[:2], 1):
        print(f"     片段{i}（{len(c.page_content)}字）: {c.page_content[:40]}...")

    print("第 4 步：向量化写入 Chroma")
    count = add_documents(TEST_KB_ID, chunks)
    print(f"  -> 已写入 {count} 个向量")

    print("第 5 步：相似度检索")
    query = "退货的运费谁来承担？"
    hits = retrieve(TEST_KB_ID, query, top_k=2)
    for doc, score in hits:
        print(f"  -> 相似度 {score:.3f} | {doc.page_content[:60]}...")

    print("第 6 步：流式生成回答")
    print("  -> 回答：", end="")
    answer = ""
    for token in stream_generate(query, hits, history=[]):
        answer += token
        print(token, end="", flush=True)
    print()
    print("=" * 60)
    print(f"完整回答：{answer}")

    print("清理：删除测试知识库向量数据")
    delete_collection(TEST_KB_ID)
    print("验证完成，RAG 全流程 OK")


if __name__ == "__main__":
    main()
