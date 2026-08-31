"""Schema 共享基类：统一时间字段的序列化口径

为什么需要这个基类（面试可讲）：
- 系统内部统一用 UTC 存储时间（数据库存「绝对时间」，不随部署环境/容器时区漂移）
- 但 MySQL DATETIME 列不带时区，SQLAlchemy 读出来是「没有时区标记的 naive 值」
- 若直接序列化输出（如 2026-08-31T06:05:02），前端 new Date() 会按浏览器本地时区解析，
  容器跑在 UTC 时用户看到的时间就会慢 8 小时
- 本基类在序列化时给 naive datetime 补上 UTC 时区，输出 ISO 8601 带 Z 后缀，
  前端 new Date() 自动转换为用户本地时区显示，两端语义正确
"""
from datetime import datetime, timezone

from pydantic import BaseModel, field_serializer


class UTCDateTimeModel(BaseModel):
    """所有含时间字段的响应模型继承它：naive datetime 按 UTC 补时区后输出"""

    @field_serializer("*")
    def _serialize_naive_datetime_as_utc(self, value, _info):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
