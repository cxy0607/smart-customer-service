"""Alembic 迁移环境配置

- 数据库连接串复用应用配置（app.config 读取 .env），不在 alembic.ini 中硬编码
- target_metadata 指向 ORM 模型的统一元数据，支持 autogenerate 自动生成迁移脚本
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# 保证可导入 app 包（alembic 命令从 backend 目录执行，也可从容器内执行）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app import models  # noqa: E402,F401  导入所有模型，注册到 metadata

config = context.config

# 从应用配置读取数据库连接串，覆盖 alembic.ini 中的占位值
config.set_main_option("sqlalchemy.url", get_settings().mysql_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL，不连数据库"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
