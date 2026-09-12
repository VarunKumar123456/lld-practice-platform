"""
Domain model.

Entity responsibilities
------------------------
Problem      : Immutable practice content (title, prompt, requirements).
Attempt      : One learner's *session* against one Problem. Owns the
               practice-loop state (IN_PROGRESS -> SUBMITTED). A learner may
               have many Attempts at the same Problem -- this is what makes
               "try again" and History meaningful instead of one-shot solving.
Submission   : One piece of work handed in for an Attempt. An Attempt can
               have multiple Submissions (resubmit after feedback) — the
               Attempt does not "become" the submission, it *collects* them.
Evaluation   : The result of running one Evaluator against one Submission.
               A Submission can have more than one Evaluation (deterministic
               + LLM), which is what lets us mix evaluation strategies
               instead of forcing a single verdict.
FeedbackItem : One atomic, explainable piece of feedback belonging to an
               Evaluation (category + message + severity + suggestion).
               Keeping this as its own row (not a blob of text) is what
               makes feedback structured/explainable rather than "an essay
               from the AI".

Why split Attempt vs Submission vs Evaluation into three tables instead of
one wide "attempts" table: each has an independent lifecycle and a
different extension axis --
  * Attempt varies by *problem type* (future: timed attempts, hints used).
  * Submission varies by *format* (text / code / diagram) — the SubmissionFormat
    enum is exactly the seam a new format plugs into.
  * Evaluation varies by *strategy* (deterministic / LLM / future: static
    analysis, peer review) — EvaluatorType is that seam.
Collapsing these would couple "what a learner wrote" to "how we judged it",
which is precisely the flexibility the assignment asks for (Design Question:
"accommodate another evaluation approach or submission format later").
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum as SAEnum, Integer, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Difficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"


class SubmissionFormat(str, enum.Enum):
    TEXT = "TEXT"        # prose design explanation
    CODE = "CODE"        # class/interface code
    DIAGRAM = "DIAGRAM"  # textual UML-ish description (mermaid/plantuml-like)


class SubmissionStatus(str, enum.Enum):
    PENDING = "PENDING"        # queued, evaluation not started
    EVALUATING = "EVALUATING"  # background evaluation running
    COMPLETED = "COMPLETED"    # evaluation finished successfully
    FAILED = "FAILED"          # evaluation raised/timed-out; retry-able


class EvaluatorType(str, enum.Enum):
    DETERMINISTIC = "DETERMINISTIC"
    LLM = "LLM"


class Severity(str, enum.Enum):
    INFO = "INFO"
    SUGGESTION = "SUGGESTION"
    ISSUE = "ISSUE"
    CRITICAL = "CRITICAL"


class Problem(Base):
    __tablename__ = "problems"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    difficulty = Column(SAEnum(Difficulty), nullable=False, default=Difficulty.MEDIUM)
    summary = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=False)   # list[str]
    constraints = Column(JSON, nullable=False)    # list[str]
    expected_concepts = Column(JSON, nullable=False)  # list[str] e.g. ["State pattern", "Strategy"]
    created_at = Column(DateTime, default=datetime.utcnow)

    attempts = relationship("Attempt", back_populates="problem")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(String, primary_key=True, default=_uuid)
    problem_id = Column(String, ForeignKey("problems.id"), nullable=False)
    learner_id = Column(String, nullable=False, default="demo-learner")  # no auth in MVP
    status = Column(SAEnum(AttemptStatus), nullable=False, default=AttemptStatus.IN_PROGRESS)
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    problem = relationship("Problem", back_populates="attempts")
    submissions = relationship(
        "Submission", back_populates="attempt", order_by="Submission.submitted_at"
    )

    def mark_submitted(self):
        self.status = AttemptStatus.SUBMITTED
        self.submitted_at = datetime.utcnow()


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=_uuid)
    attempt_id = Column(String, ForeignKey("attempts.id"), nullable=False)
    format = Column(SAEnum(SubmissionFormat), nullable=False, default=SubmissionFormat.TEXT)
    content = Column(Text, nullable=False)
    status = Column(SAEnum(SubmissionStatus), nullable=False, default=SubmissionStatus.PENDING)
    attempt_number = Column(Integer, nullable=False, default=1)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    failure_reason = Column(Text, nullable=True)

    attempt = relationship("Attempt", back_populates="submissions")
    evaluations = relationship(
        "Evaluation", back_populates="submission", order_by="Evaluation.created_at"
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String, primary_key=True, default=_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    evaluator_type = Column(SAEnum(EvaluatorType), nullable=False)
    score = Column(Integer, nullable=True)  # 0-100, nullable until computed
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="evaluations")
    feedback_items = relationship("FeedbackItem", back_populates="evaluation")


class FeedbackItem(Base):
    __tablename__ = "feedback_items"

    id = Column(String, primary_key=True, default=_uuid)
    evaluation_id = Column(String, ForeignKey("evaluations.id"), nullable=False)
    category = Column(String, nullable=False)  # e.g. "Responsibility", "Extensibility"
    severity = Column(SAEnum(Severity), nullable=False, default=Severity.SUGGESTION)
    message = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=True)

    evaluation = relationship("Evaluation", back_populates="feedback_items")
