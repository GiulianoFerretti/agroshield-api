from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.db import get_db
from app.models import Client, User
from app.auth import get_current_user

VALID_PERSON_TYPES = {"individual", "company"}


class ClientCreate(BaseModel):
    name: str
    person_type: str
    tax_id: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("person_type")
    @classmethod
    def validate_person_type(cls, v: str) -> str:
        if v not in VALID_PERSON_TYPES:
            raise ValueError("person_type must be 'individual' or 'company'")
        return v

    @field_validator("tax_id")
    @classmethod
    def normalize_tax_id(cls, v: str) -> str:
        digits = "".join(filter(str.isdigit, v))
        if not digits:
            raise ValueError("tax_id must contain digits")
        return digits


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    person_type: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("person_type")
    @classmethod
    def validate_person_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PERSON_TYPES:
            raise ValueError("person_type must be 'individual' or 'company'")
        return v

    @field_validator("tax_id")
    @classmethod
    def normalize_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            digits = "".join(filter(str.isdigit, v))
            if not digits:
                raise ValueError("tax_id must contain digits")
            return digits
        return v


router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", status_code=201)
def create_client(
    payload: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Client).filter(
        Client.user_id == current_user.id,
        Client.tax_id == payload.tax_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="tax_id already registered for this account")

    client = Client(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("")
def list_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Client).filter(Client.user_id == current_user.id).all()


@router.get("/{client_id}")
def get_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.patch("/{client_id}")
def update_client(
    client_id: str,
    payload: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    changes = payload.model_dump(exclude_unset=True)

    if "tax_id" in changes:
        conflict = db.query(Client).filter(
            Client.user_id == current_user.id,
            Client.tax_id == changes["tax_id"],
            Client.id != client_id,
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="tax_id already registered for this account")

    for field, value in changes.items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return client
