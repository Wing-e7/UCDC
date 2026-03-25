from __future__ import annotations

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
    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

