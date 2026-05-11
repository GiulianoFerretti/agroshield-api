from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
import hashlib

from app.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def _normalize_password(password: str) -> str:
    b = password.encode("utf-8")
    # bcrypt aceita no máximo 72 bytes; se passar disso, pré-hash para tamanho fixo
    if len(b) > 72:
        return hashlib.sha256(b).hexdigest()
    return password


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_password(password), hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
