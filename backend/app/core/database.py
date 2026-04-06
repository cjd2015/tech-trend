import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 数据库配置 - 使用 SQLite 作为初始数据库，便于开发
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crucix_refactor.db")

is_sqlite = DATABASE_URL.startswith("sqlite")
engine_kwargs = {
    "echo": False,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # 仅在内存 SQLite 下使用 StaticPool，文件型 SQLite 使用默认连接池更稳定。
    if DATABASE_URL.endswith(":memory:") or "mode=memory" in DATABASE_URL:
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """依赖注入数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
