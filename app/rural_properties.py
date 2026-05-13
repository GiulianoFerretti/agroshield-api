from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.db import get_db
from app.models import Client, RuralProperty, User
from app.auth import get_current_user


class RuralPropertyCreate(BaseModel):
    client_id: str
    name: str
    state: str
    city: str
    total_area_hectares: Optional[float] = None
    main_activity: Optional[str] = None
    notes: Optional[str] = None


class RuralPropertyUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    total_area_hectares: Optional[float] = None
    main_activity: Optional[str] = None
    notes: Optional[str] = None


router = APIRouter(prefix="/rural-properties", tags=["rural-properties"])


def _get_owned_property(
    property_id: str,
    current_user: User,
    db: Session,
) -> RuralProperty:
    prop = (
        db.query(RuralProperty)
        .join(Client, Client.id == RuralProperty.client_id)
        .filter(
            RuralProperty.id == property_id,
            Client.user_id == current_user.id,
        )
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Rural property not found")
    return prop


@router.post("", status_code=201)
def create_rural_property(
    payload: RuralPropertyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(
        Client.id == payload.client_id,
        Client.user_id == current_user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    prop = RuralProperty(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("")
def list_rural_properties(
    client_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(RuralProperty)
        .join(Client, Client.id == RuralProperty.client_id)
        .filter(Client.user_id == current_user.id)
    )
    if client_id:
        query = query.filter(RuralProperty.client_id == client_id)
    return query.all()


@router.get("/{property_id}")
def get_rural_property(
    property_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_property(property_id, current_user, db)


@router.patch("/{property_id}")
def update_rural_property(
    property_id: str,
    payload: RuralPropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prop = _get_owned_property(property_id, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    db.commit()
    db.refresh(prop)
    return prop
