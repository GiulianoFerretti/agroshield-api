from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.db import get_db
from app.models import (
    Assessment,
    AssessmentAnswer,
    AnswerOption,
    Client,
    Question,
    RuralProperty,
    User,
)
from app.auth import get_current_user


VALID_ASSESSMENT_STATUSES = {"draft", "completed", "archived"}


class AssessmentCreate(BaseModel):
    rural_property_id: str
    notes: Optional[str] = None


class AssessmentAnswerCreate(BaseModel):
    question_id: str
    answer_option_id: str


router = APIRouter(prefix="/assessments", tags=["assessments"])


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


def _get_owned_assessment(
    assessment_id: str,
    current_user: User,
    db: Session,
) -> Assessment:
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id,
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


def _risk_level_from_score(score: float) -> str:
    if score <= 0.25:
        return "low"
    if score <= 0.50:
        return "medium"
    if score <= 0.75:
        return "high"
    return "critical"


@router.post("", status_code=201)
def create_assessment(
    payload: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_property(payload.rural_property_id, current_user, db)

    assessment = Assessment(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        rural_property_id=payload.rural_property_id,
        status="draft",
        notes=payload.notes,
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("")
def list_assessments(
    rural_property_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Assessment).filter(Assessment.user_id == current_user.id)

    if rural_property_id:
        query = query.filter(Assessment.rural_property_id == rural_property_id)

    if status:
        if status not in VALID_ASSESSMENT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid assessment status")
        query = query.filter(Assessment.status == status)

    return query.order_by(Assessment.created_at.desc()).all()


@router.get("/{assessment_id}")
def get_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_assessment(assessment_id, current_user, db)



@router.get("/{assessment_id}/report")
def get_assessment_report(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = _get_owned_assessment(assessment_id, current_user, db)

    prop = db.query(RuralProperty).filter(
        RuralProperty.id == assessment.rural_property_id,
    ).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Rural property not found")

    answers = (
        db.query(AssessmentAnswer)
        .filter(AssessmentAnswer.assessment_id == assessment_id)
        .all()
    )

    report_answers = []

    for answer in answers:
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        option = db.query(AnswerOption).filter(AnswerOption.id == answer.answer_option_id).first()

        report_answers.append({
            "question_id": answer.question_id,
            "question": question.text if question else None,
            "answer_option_id": answer.answer_option_id,
            "selected_answer": option.text if option else None,
            "weight": answer.weight,
        })

    recommendations = []

    high_risk_answers = [
        item for item in report_answers
        if item["weight"] >= 0.75
    ]

    if assessment.risk_level == "critical":
        recommendations.append({
            "priority": "critical",
            "title": "Immediate action recommended",
            "description": "The assessment indicates critical risk. Prioritize correction of the highest-risk items before audits, inspections, new contracts, or operational expansion."
        })
    elif assessment.risk_level == "high":
        recommendations.append({
            "priority": "high",
            "title": "Priority correction plan",
            "description": "The assessment indicates high risk. Prepare a correction plan with responsible parties, deadlines, and documentary evidence."
        })
    elif assessment.risk_level == "medium":
        recommendations.append({
            "priority": "medium",
            "title": "Preventive monitoring",
            "description": "The assessment indicates medium risk. Review documents, internal controls, and evidence before the risk level increases."
        })
    elif assessment.risk_level == "low":
        recommendations.append({
            "priority": "low",
            "title": "Maintain compliance",
            "description": "The assessment indicates low risk. Keep documents updated and perform periodic monitoring."
        })

    for item in high_risk_answers:
        recommendations.append({
            "priority": "high",
            "title": "Critical item identified",
            "description": f"The answer '{item['selected_answer']}' to the question '{item['question']}' has risk weight {item['weight']}. Treat this item as a correction priority."
        })

    risk_messages = {
        "low": "The assessment indicates low risk.",
        "medium": "The assessment indicates medium risk.",
        "high": "The assessment indicates high risk.",
        "critical": "The assessment indicates critical risk.",
    }

    return {
        "assessment": {
            "id": assessment.id,
            "status": assessment.status,
            "total_score": assessment.total_score,
            "risk_level": assessment.risk_level,
            "created_at": assessment.created_at,
            "updated_at": assessment.updated_at,
        },
        "property": {
            "id": prop.id,
            "name": prop.name,
            "city": prop.city,
            "state": prop.state,
            "main_activity": prop.main_activity,
            "total_area_hectares": prop.total_area_hectares,
        },
        "answers": report_answers,
        "recommendations": recommendations,
        "summary": {
            "risk_level": assessment.risk_level,
            "message": risk_messages.get(
                assessment.risk_level,
                "The assessment does not have a risk classification yet.",
            ),
        },
    }
@router.post("/{assessment_id}/answers", status_code=201)
def upsert_assessment_answer(
    assessment_id: str,
    payload: AssessmentAnswerCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = _get_owned_assessment(assessment_id, current_user, db)

    if assessment.status != "draft":
        raise HTTPException(status_code=400, detail="Assessment is not editable")

    question = db.query(Question).filter(
        Question.id == payload.question_id,
        Question.is_active == True,
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    option = db.query(AnswerOption).filter(
        AnswerOption.id == payload.answer_option_id,
        AnswerOption.question_id == payload.question_id,
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Answer option not found for this question")

    existing = db.query(AssessmentAnswer).filter(
        AssessmentAnswer.assessment_id == assessment_id,
        AssessmentAnswer.question_id == payload.question_id,
    ).first()

    if existing:
        existing.answer_option_id = payload.answer_option_id
        existing.weight = option.weight
        db.commit()
        db.refresh(existing)
        response.status_code = 200
        return existing

    answer = AssessmentAnswer(
        id=str(uuid.uuid4()),
        assessment_id=assessment_id,
        question_id=payload.question_id,
        answer_option_id=payload.answer_option_id,
        weight=option.weight,
    )

    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


@router.get("/{assessment_id}/answers")
def list_assessment_answers(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_assessment(assessment_id, current_user, db)

    return (
        db.query(AssessmentAnswer)
        .filter(AssessmentAnswer.assessment_id == assessment_id)
        .all()
    )


@router.post("/{assessment_id}/complete")
def complete_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = _get_owned_assessment(assessment_id, current_user, db)

    if assessment.status != "draft":
        raise HTTPException(status_code=400, detail="Assessment is not in draft status")

    answers = (
        db.query(AssessmentAnswer)
        .filter(AssessmentAnswer.assessment_id == assessment_id)
        .all()
    )

    if not answers:
        raise HTTPException(status_code=400, detail="Assessment has no answers")

    total_score = sum(answer.weight for answer in answers) / len(answers)

    assessment.total_score = total_score
    assessment.risk_level = _risk_level_from_score(total_score)
    assessment.status = "completed"

    db.commit()
    db.refresh(assessment)
    return assessment
