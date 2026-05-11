from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _with_charset(url: str) -> str:
    if "?" in url:
        return url
    return f"{url}?charset=utf8mb4"


def _engine_kwargs(url_str: str) -> dict[str, Any]:
    """避免 MySQL 不可达时连接长时间挂死，导致前端 axios 先超时。"""
    url = make_url(url_str)
    kw: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_timeout": 15,
        "pool_recycle": 1200,
        "pool_size": 5,
        "max_overflow": 10,
    }
    if url.drivername.startswith("mysql"):
        kw["connect_args"] = {
            "connect_timeout": 5,
            "read_timeout": 30,
            "write_timeout": 30,
        }
        kw["pool_size"] = 10
        kw["max_overflow"] = 20
    return kw


engine = create_engine(_with_charset(settings.database_url), **_engine_kwargs(settings.database_url))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
