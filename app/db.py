import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

_engine = None
_SessionLocal = None

def _ensure():
    global _engine, _SessionLocal
    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL não configurada no serviço agroshield-api.")
        _engine = create_engine(database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine, _SessionLocal

def get_engine():
    eng, _ = _ensure()
    return eng

def get_db():
    _, SessionLocal = _ensure()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
