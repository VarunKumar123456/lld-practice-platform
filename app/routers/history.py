from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt
from app.schemas import AttemptHistoryOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/{learner_id}", response_model=List[AttemptHistoryOut])
def get_history(learner_id: str, db: Session = Depends(get_db)):
    attempts = (
        db.query(Attempt)
        .filter(Attempt.learner_id == learner_id)
        .order_by(Attempt.started_at.desc())
        .all()
    )
    return [
        AttemptHistoryOut(attempt=a, problem=a.problem, submissions=a.submissions)
        for a in attempts
    ]
