"""Schema 序列化测试：时间字段的时区口径

背景：曾出现「容器 UTC 时间被前端当本地时间显示，慢 8 小时」的 bug。
根因是 MySQL DATETIME 不带时区、SQLAlchemy 读出 naive 值、序列化无时区后缀。
修复约定：内部统一 UTC 存储，输出必须带时区后缀（Z 或 +00:00），
前端 new Date() 才能正确转用户本地时区。本测试防止回归。
"""
from datetime import datetime

from app.schemas.kb import DocumentOut, KnowledgeBaseOut


def _extract_created_at(schema) -> str:
    """取 JSON 输出中的 created_at 字符串"""
    return schema.model_dump_json().split('"created_at":"')[1].split('"')[0]


def test_created_at_序列化必须带时区后缀():
    """naive datetime 应按 UTC 补时区输出（Z 或 +00:00），前端才能正确转换"""
    kb = KnowledgeBaseOut(
        id=1, name="测试库", description="",
        created_at=datetime(2026, 8, 31, 6, 5, 2),
    )
    ts = _extract_created_at(kb)
    assert ts.endswith("Z") or ts.endswith("+00:00"), f"缺少时区后缀: {ts}"
    assert ts.startswith("2026-08-31T06:05:02"), f"UTC 数值被改动: {ts}"


def test_document_created_at_同样带时区后缀():
    """所有含时间字段的 Out 模型都继承同一基类，行为一致"""
    doc = DocumentOut(
        id=1, kb_id=1, filename="a.pdf", size=100,
        status="succeeded", chunk_count=2, error_msg="",
        created_at=datetime(2026, 8, 31, 6, 5, 2),
    )
    ts = _extract_created_at(doc)
    assert ts.endswith("Z") or ts.endswith("+00:00"), f"缺少时区后缀: {ts}"
