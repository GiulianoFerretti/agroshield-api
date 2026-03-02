from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
import os

from .db import engine, get_db, Base
from .models import User

app = FastAPI()

# 🔹 Criar tabelas automaticamente ao subir a aplicação
Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"ok": False, "error": "DATABASE_URL não configurada"}

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    return {"ok": True, "select_1": result}


@app.get("/users-count")
def users_count(db: Session = Depends(get_db)):
    count = db.query(User).count()
    return {"users": count}
