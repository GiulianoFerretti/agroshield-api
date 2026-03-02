from fastapi import FastAPI
from sqlalchemy import create_engine, text
import os

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-check")
def db_check():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"ok": False, "error": "DATABASE_URL não configurada"}

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    return {"ok": True, "select_1": result}
