"""
Evaluation pipeline.

Answers "what should happen if evaluation takes time or fails?" pragmatically
(no queues/distributed workers for a 2-day MVP):

  1. On submit, the Submission is created with status=PENDING and returned
     to the caller immediately (submission is never blocked on evaluation).
  2. A FastAPI BackgroundTask runs `run_evaluation_pipeline` after the
     response is sent. Status moves PENDING -> EVALUATING -> COMPLETED.
  3. Each evaluator is run independently and defensively: if one evaluator
     raises, that failure is captured as a single INFO-level feedback item
     for that evaluator rather than failing the whole submission — a
     learner should still get deterministic feedback even if the LLM call
     errors, and vice versa.
  4. Only if *no* evaluator produced a usable result does the submission
     move to FAILED (with `failure_reason` set) so the learner can retry.
  5. Retries are just "submit again" (a new Submission row against the same
     Attempt) — no special retry machinery needed for this scope.

This intentionally stops short of a job queue / worker pool / retries-with-
backoff, per the assignment's explicit scope boundary against turning this
into a distributed-systems project.
"""
from typing import List

from sqlalchemy.orm import Session

from app.evaluation.base import Evaluator, EvaluationResult, FeedbackItemResult
from app.evaluation.deterministic import DeterministicEvaluator
from app.evaluation.llm_evaluator import build_llm_evaluator
from app.models import (
    Submission, SubmissionStatus, Evaluation, FeedbackItem, Problem,
)


def get_evaluators() -> List[Evaluator]:
    """
    Registry of active evaluators. Adding a new evaluation approach later
    (e.g. a static-analysis evaluator for CODE submissions, or a peer-review
    evaluator) means appending one line here — the pipeline loop below,
    the API routes, and the DB schema all stay unchanged.
    """
    return [DeterministicEvaluator(), build_llm_evaluator()]


def run_evaluation_pipeline(submission_id: str, db: Session) -> None:
    submission = db.query(Submission).get(submission_id)
    if submission is None:
        return

    problem = db.query(Problem).get(submission.attempt.problem_id)
    submission.status = SubmissionStatus.EVALUATING
    db.commit()

    results: List[EvaluationResult] = []
    for evaluator in get_evaluators():
        try:
            result = evaluator.evaluate(
                submission_content=submission.content,
                submission_format=submission.format.value,
                problem_summary=problem.summary,
                requirements=problem.requirements,
                constraints=problem.constraints,
                expected_concepts=problem.expected_concepts,
            )
        except Exception as exc:  # noqa: BLE001 - one evaluator's crash must not sink the submission
            result = EvaluationResult(
                evaluator_type=getattr(evaluator, "name", "unknown").upper(),
                score=None,
                summary="This evaluator failed and was skipped.",
                feedback_items=[FeedbackItemResult(
                    category="Evaluator Error",
                    message=f"{evaluator.__class__.__name__} raised "
                            f"{exc.__class__.__name__}: {exc}",
                )],
            )
        results.append(result)

    if not results:
        submission.status = SubmissionStatus.FAILED
        submission.failure_reason = "No evaluators produced a result."
        db.commit()
        return

    for result in results:
        evaluation = Evaluation(
            submission_id=submission.id,
            evaluator_type=result.evaluator_type,
            score=result.score,
            summary=result.summary,
        )
        db.add(evaluation)
        db.flush()  # get evaluation.id before inserting children
        for fi in result.feedback_items:
            db.add(FeedbackItem(
                evaluation_id=evaluation.id,
                category=fi.category,
                severity=fi.severity,
                message=fi.message,
                suggestion=fi.suggestion,
            ))

    submission.status = SubmissionStatus.COMPLETED
    db.commit()
