from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.evaluation.pipeline import run_evaluation_pipeline
from app.models import Attempt, Problem, Submission, SubmissionStatus
from app.schemas import AttemptCreate, AttemptOut, SubmissionCreate, SubmissionOut

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.post("", response_model=AttemptOut)
def start_attempt(payload: AttemptCreate, db: Session = Depends(get_db)):
    problem = db.query(Problem).get(payload.problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")
    attempt = Attempt(problem_id=payload.problem_id, learner_id=payload.learner_id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def _run_pipeline_isolated(submission_id: str):
    """
    Background tasks run after the request's DB session is closed, so this
    opens its own session rather than reusing the request-scoped one from
    Depends(get_db) — sharing a session across the request/background
    boundary is a common source of "session is closed" bugs.
    """
    db = SessionLocal()
    try:
        run_evaluation_pipeline(submission_id, db)
    finally:
        db.close()


@router.post("/{attempt_id}/submissions", response_model=SubmissionOut)
def submit_solution(
    attempt_id: str,
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    attempt = db.query(Attempt).get(attempt_id)
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    attempt_number = len(attempt.submissions) + 1
    submission = Submission(
        attempt_id=attempt_id,
        format=payload.format,
        content=payload.content,
        status=SubmissionStatus.PENDING,
        attempt_number=attempt_number,
    )
    db.add(submission)
    attempt.mark_submitted()
    db.commit()
    db.refresh(submission)

    background_tasks.add_task(_run_pipeline_isolated, submission.id)
    return submission


@router.get("/{attempt_id}/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(attempt_id: str, submission_id: str, db: Session = Depends(get_db)):
    submission = db.query(Submission).get(submission_id)
    if not submission or submission.attempt_id != attempt_id:
        raise HTTPException(404, "Submission not found")
    return submission
