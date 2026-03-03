from fastapi.security import OAuth2PasswordRequestForm
from app.security import verify_password, create_access_token

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

from pydantic import BaseModel

class RegisterInput(BaseModel):
    name: str
    email: str
    password: str
@router.post("/register")
def register(
    payload: RegisterInput,
    db: Session = Depends(get_db)
):
    try:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email já cadastrado")

        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role="admin",
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token(subject=user.email)
    return {"access_token": token, "token_type": "bearer"}
        
        return {"message": "Usuário criado com sucesso"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
