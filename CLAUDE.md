# 智能客服问答系统 — 项目文档

## 项目概述

**项目名称**：智能客服问答系统（smart-customer-service）
**项目类型**：Web 应用（企业级 AI 客服平台）
**目标用户**：企业客服团队（管理员维护知识库，访客提问）
**用途**：实践项目 + 实际可部署运行的 AI 应用

---

## 技术栈

| 层面 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI + Pydantic v2 | 异步高性能、自动 OpenAPI 文档 |
| AI 框架 | LangChain 1.x | 文档加载/切分/向量库/检索编排 |
| 大模型 | 阿里云百炼（qwen-plus + text-embedding-v3） | OpenAI 兼容接口，封装层解耦厂商 |
| 向量库 | Chroma | 嵌入式向量库，按知识库分 collection 隔离 |
| 数据库 | MySQL 8 + SQLAlchemy 2.x + Alembic | 业务数据存储 + 迁移版本管理 |
| 缓存 | Redis 7 | 滑动窗口限流 |
| 前端 | Vue3 + Vite + Element Plus + Pinia | 管理后台，SSE 流式对话 |
| 测试 | pytest + vitest | 后端 16 用例 + 前端 26 用例 |
| 部署 | Docker Compose | mysql/redis/backend/frontend 四服务编排 |

---

## ⭐ 协作规则（极其重要）

**本项目是用户的实践项目，用户是 AI 应用开发方向的开发者。**

在整个项目开发过程中，必须严格遵守以下规则：

1. **任何技术决策，由 Claude 列出多个方案**，解释每个方案的优缺点与技术价值，让用户做选择。
2. **代码注释和文档用中文**，关键设计点要在注释中写明"为什么这样设计"（设计说明）。
3. **每完成一个功能/阶段，主动向用户解释**：做了什么、核心逻辑是什么、技术评审可能会怎么问——帮助用户真正吃透代码，而不是只"做出来"。
4. **遇到技术问题时，主动排查并提出解决方案**，修复后说明问题根因（踩坑过程值得记录）。
5. **保持代码分层清晰**：api（路由）/ services（业务）/ rag（检索生成）/ core（基础设施），新代码遵循现有分层。
6. **改动前后端接口契约时，同步更新测试**，保证 `pytest` 全绿。

---

## 项目结构

```
project1/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/                # 路由层（auth/kb/documents/faqs/chat/admin/health）
│   │   ├── core/               # 日志、统一异常、JWT、限流、请求ID中间件
│   │   ├── llm/                # 百炼封装（对话模型 + 自定义 Embeddings）
│   │   ├── rag/                # RAG 流水线（加载/切分/向量库/检索生成）
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── schemas/            # Pydantic 契约
│   │   └── services/           # 业务逻辑（文档状态机/FAQ一致性/对话流程）
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # pytest 测试
│   └── scripts/rag_demo.py     # RAG 流水线验证脚本
├── frontend/                   # Vue3 管理后台
│   └── src/
│       ├── views/              # 登录/试聊/知识库/文档/FAQ/记录/统计
│       ├── api/                # Axios 封装 + 接口定义
│       ├── utils/sse.js        # SSE 流式解析
│       ├── stores/             # Pinia 状态
│       └── router/             # 路由 + 守卫
├── docker-compose.yml          # 四服务编排
└── .env.example                # 环境变量模板（.env 不入库）
```

---

## 开发命令参考

| 命令 | 作用 | 执行目录 |
|------|------|---------|
| `.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000` | 启动后端开发服务器 | backend/ |
| `.venv/Scripts/python -m pytest tests/ -v` | 运行后端测试 | backend/ |
| `.venv/Scripts/alembic revision --autogenerate -m "说明"` | 生成数据库迁移 | backend/ |
| `npm run dev` | 启动前端开发服务器（5173，代理 /api 到 8000） | frontend/ |
| `npm run build` | 构建前端生产包 | frontend/ |
| `npm test` | 运行前端测试（vitest） | frontend/ |
| `docker compose up -d --build` | 一键部署（含前端构建） | 项目根 |


- **提交门禁**：`git commit` 自动触发（PreToolUse hook），先跑后端 pytest + 前端 vitest + 前端构建，全过才放行
- **质量工程师 agent**（quality-engineer）：五维度代码质量审查（安全/注释/错误处理/规范/性能）
- **测试专员 agent**（tester1）：编写/运行 pytest 测试
- **/git-save**：带双重门禁的保存流程（tester1 + quality-engineer 全过才提交）

---

## 更新日志

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-08-31 | v1.0 | 项目完成：7 阶段开发、16 测试全绿、Docker 部署验证、推送 GitHub |
