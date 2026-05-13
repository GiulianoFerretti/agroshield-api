from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.db import get_db
from app.models import AnswerOption, Question, User
from app.auth import get_current_user, require_admin

VALID_QUESTION_TYPES = {"multiple_choice", "yes_no", "scale"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    text: str
    category: str
    question_type: str
    sort_order: int = 0

    @field_validator("question_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_QUESTION_TYPES:
            raise ValueError(f"question_type must be one of {VALID_QUESTION_TYPES}")
        return v


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    category: Optional[str] = None
    question_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("question_type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_QUESTION_TYPES:
            raise ValueError(f"question_type must be one of {VALID_QUESTION_TYPES}")
        return v


class AnswerOptionCreate(BaseModel):
    text: str
    weight: float
    sort_order: int = 0

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("weight must be between 0.0 and 1.0")
        return v


class AnswerOptionUpdate(BaseModel):
    text: Optional[str] = None
    weight: Optional[float] = None
    sort_order: Optional[int] = None

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("weight must be between 0.0 and 1.0")
        return v


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/questions", tags=["questions"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_question_or_404(question_id: str, db: Session) -> Question:
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


# ── Question endpoints ────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_question(
    payload: QuestionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    question = Question(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("")
def list_questions(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Question)
    if not (include_inactive and current_user.role == "admin"):
        query = query.filter(Question.is_active == True)
    return query.order_by(Question.sort_order).all()


@router.get("/{question_id}")
def get_question(
    question_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_question_or_404(question_id, db)


@router.patch("/{question_id}")
def update_question(
    question_id: str,
    payload: QuestionUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(question_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question


# ── AnswerOption endpoints ────────────────────────────────────────────────────

@router.post("/{question_id}/options", status_code=201)
def create_option(
    question_id: str,
    payload: AnswerOptionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _get_question_or_404(question_id, db)
    option = AnswerOption(
        id=str(uuid.uuid4()),
        question_id=question_id,
        **payload.model_dump(),
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


@router.get("/{question_id}/options")
def list_options(
    question_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_question_or_404(question_id, db)
    return (
        db.query(AnswerOption)
        .filter(AnswerOption.question_id == question_id)
        .order_by(AnswerOption.sort_order)
        .all()
    )


@router.patch("/{question_id}/options/{option_id}")
def update_option(
    question_id: str,
    option_id: str,
    payload: AnswerOptionUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _get_question_or_404(question_id, db)
    option = db.query(AnswerOption).filter(
        AnswerOption.id == option_id,
        AnswerOption.question_id == question_id,
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Answer option not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(option, field, value)
    db.commit()
    db.refresh(option)
    return option
