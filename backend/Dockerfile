# 后端镜像：FastAPI 应用
# 启动流程：alembic 迁移建表 -> uvicorn 启动（多阶段不必要，slim 基础镜像已足够小）
FROM python:3.13-slim

WORKDIR /app

# 国内环境使用清华源加速安装
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 先复制依赖清单再安装：利用 Docker 层缓存，代码变动时无需重装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码与迁移脚本
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# 启动前先执行数据库迁移（企业标准做法：结构变更随版本走，不用 create_all 兜底）
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
