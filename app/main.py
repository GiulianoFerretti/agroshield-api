from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import engine, get_db, Base
from app.models import User

app = FastAPI()
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    return {"ok": True, "select_1": result}

@app.get("/users-count")
def users_count(db: Session = Depends(get_db)):
    return {"users": db.query(User).count()}
from app.auth import router as auth_router
from app.admin import router as admin_router
app.include_router(auth_router)
app.include_router(admin_router)
