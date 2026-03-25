from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base

_engine = None
_sessionmaker = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    return _engine


def get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _sessionmaker


def init_db() -> None:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite"):
        Base.metadata.create_all(bind=get_engine())
        return

    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    alembic_ini = root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

