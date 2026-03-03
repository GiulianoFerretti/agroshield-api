from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(
    name: str,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email já cadastrado")

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {"message": "Usuário criado com sucesso"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
