"""模型统一导出：必须 import 全部模型，Base.metadata.create_all 才能建出所有表"""
from app.models.chat import Conversation, Message
from app.models.kb import Document, Faq, KnowledgeBase
from app.models.user import User

__all__ = ["User", "KnowledgeBase", "Document", "Faq", "Conversation", "Message"]
