from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models import (
    Difficulty, AttemptStatus, SubmissionFormat, SubmissionStatus,
    EvaluatorType, Severity,
)


class ProblemOut(BaseModel):
    id: str
    title: str
    difficulty: Difficulty
    summary: str
    requirements: List[str]
    constraints: List[str]
    expected_concepts: List[str]

    class Config:
        from_attributes = True


class ProblemListItem(BaseModel):
    id: str
    title: str
    difficulty: Difficulty
    summary: str

    class Config:
        from_attributes = True


class AttemptCreate(BaseModel):
    problem_id: str
    learner_id: str = "demo-learner"


class AttemptOut(BaseModel):
    id: str
    problem_id: str
    learner_id: str
    status: AttemptStatus
    started_at: datetime
    submitted_at: Optional[datetime]

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    format: SubmissionFormat = SubmissionFormat.TEXT
    content: str = Field(..., min_length=1)


class FeedbackItemOut(BaseModel):
    category: str
    severity: Severity
    message: str
    suggestion: Optional[str]

    class Config:
        from_attributes = True


class EvaluationOut(BaseModel):
    id: str
    evaluator_type: EvaluatorType
    score: Optional[int]
    summary: Optional[str]
    created_at: datetime
    feedback_items: List[FeedbackItemOut]

    class Config:
        from_attributes = True


class SubmissionOut(BaseModel):
    id: str
    attempt_id: str
    format: SubmissionFormat
    content: str
    status: SubmissionStatus
    attempt_number: int
    submitted_at: datetime
    failure_reason: Optional[str]
    evaluations: List[EvaluationOut] = []

    class Config:
        from_attributes = True


class AttemptHistoryOut(BaseModel):
    attempt: AttemptOut
    problem: ProblemListItem
    submissions: List[SubmissionOut]

    class Config:
        from_attributes = True
