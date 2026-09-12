"""
Evaluation strategy interface.

This is the extension seam the assignment explicitly asks for:
"How would your design accommodate another evaluation approach or another
submission format later?"

Any new evaluation approach (a static-analysis linter, a peer-review queue,
a rubric grader for a different submission format) just implements
`Evaluator` and gets registered in `evaluator.py`'s pipeline — nothing in
the API layer, the database layer, or existing evaluators needs to change.
This is the Strategy pattern applied at the evaluation layer.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from app.models import Severity


@dataclass
class FeedbackItemResult:
    category: str
    message: str
    severity: Severity = Severity.SUGGESTION
    suggestion: Optional[str] = None


@dataclass
class EvaluationResult:
    evaluator_type: str  # "DETERMINISTIC" | "LLM"
    score: Optional[int]  # 0-100, None if this evaluator doesn't score
    summary: str
    feedback_items: List[FeedbackItemResult] = field(default_factory=list)


class Evaluator(ABC):
    """
    One evaluation strategy. Implementations must be side-effect free with
    respect to the DB (no writes) — they take a submission+problem "view"
    and return a result; the pipeline/router is responsible for persistence.
    This keeps evaluators independently unit-testable without a database.
    """

    name: str = "base"

    @abstractmethod
    def evaluate(self, *, submission_content: str, submission_format: str,
                 problem_summary: str, requirements: List[str],
                 constraints: List[str], expected_concepts: List[str]) -> EvaluationResult:
        raise NotImplementedError
