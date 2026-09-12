"""
Deterministic evaluator.

Design principle (answers the assignment's question "which parts of
evaluation should be deterministic, and which benefit from an LLM?"):

Deterministic checks are reserved for things that are TRUE OR FALSE
regardless of which valid design a learner chose:
  - Did they define classes/interfaces at all, or just prose?
  - Did they use any of the concepts/patterns the problem expects
    (by name, e.g. mentioning "Strategy" / "Observer" / "State")?
  - Is there a single class holding most of the responsibility keywords
    (a God Object smell), independent of which specific classes exist?
  - Did they address extensibility/trade-offs explicitly (structural
    presence of a section), regardless of whether the trade-off itself
    is *good*?
  - Basic completeness: is the submission long/structured enough to be a
    real attempt vs. a placeholder?

These are cheap, instant, and 100% reproducible — the same input always
gets the same deterministic result, which matters for learner trust ("why
did I get this score") and for keeping the LLM's job narrow (see
llm_evaluator.py for what's judgment-based instead).
"""
import re
from typing import List

from app.evaluation.base import Evaluator, EvaluationResult, FeedbackItemResult
from app.models import Severity

CLASS_PATTERN = re.compile(r"\b(class|interface|abstract class)\s+\w+", re.IGNORECASE)
RESPONSIBILITY_HINTS = re.compile(
    r"\b(responsib\w*|encapsulat\w*|single responsibility)\b", re.IGNORECASE
)
RELATIONSHIP_HINTS = re.compile(
    r"\b(extends|implements|inherits|composition|aggregat\w*|has-a|is-a|association)\b",
    re.IGNORECASE,
)
TRADEOFF_HINTS = re.compile(r"\b(trade-?off|alternative|instead of|rejected|considered)\b", re.IGNORECASE)
EXTENSIBILITY_HINTS = re.compile(r"\b(extensib\w*|pluggable|open[- ]closed|future|scal\w*)\b", re.IGNORECASE)


class DeterministicEvaluator(Evaluator):
    name = "deterministic"

    def evaluate(self, *, submission_content: str, submission_format: str,
                 problem_summary: str, requirements: List[str],
                 constraints: List[str], expected_concepts: List[str]) -> EvaluationResult:
        content = submission_content
        feedback: List[FeedbackItemResult] = []
        score = 100

        # 1. Completeness — placeholder / too-short submissions
        word_count = len(content.split())
        if word_count < 40:
            score -= 40
            feedback.append(FeedbackItemResult(
                category="Completeness",
                severity=Severity.CRITICAL,
                message=f"The submission is very short ({word_count} words), too little to "
                        f"represent classes, responsibilities, and relationships.",
                suggestion="Include at least the core classes/interfaces, their responsibilities, "
                           "and how they relate to each other.",
            ))

        # 2. Class/interface presence
        class_matches = CLASS_PATTERN.findall(content)
        if not class_matches:
            score -= 25
            feedback.append(FeedbackItemResult(
                category="Core Design",
                severity=Severity.ISSUE,
                message="No explicit class/interface definitions were detected "
                        "(no 'class X' / 'interface X' pattern found).",
                suggestion="Name your classes and interfaces explicitly, e.g. "
                           "'class ParkingSpot', 'interface PricingStrategy'.",
            ))
        else:
            feedback.append(FeedbackItemResult(
                category="Core Design",
                severity=Severity.INFO,
                message=f"Detected {len(class_matches)} class/interface declaration(s).",
            ))

        # 3. God-object smell: one class name repeated disproportionately
        # alongside many responsibility keywords suggests responsibilities
        # weren't actually distributed.
        if class_matches:
            names = [m[1] if isinstance(m, tuple) else m for m in
                     re.findall(r"\b(?:class|interface)\s+(\w+)", content, re.IGNORECASE)]
            if names:
                most_common = max(set(names), key=names.count)
                dominance = names.count(most_common) / len(names)
                if len(set(names)) == 1 and word_count > 20:
                    score -= 15
                    feedback.append(FeedbackItemResult(
                        category="Responsibility Distribution",
                        severity=Severity.ISSUE,
                        message=f"Only one class ('{most_common}') is defined despite a "
                                f"substantial submission — possible God Object.",
                        suggestion="Consider splitting responsibilities across collaborating "
                                   "classes instead of one class doing everything.",
                    ))

        # 4. Relationship vocabulary
        if not RELATIONSHIP_HINTS.search(content):
            score -= 10
            feedback.append(FeedbackItemResult(
                category="Relationships",
                severity=Severity.SUGGESTION,
                message="No explicit relationship vocabulary detected (extends/implements/"
                        "composition/association).",
                suggestion="State how your classes relate: inheritance, composition, or "
                           "association, and why.",
            ))

        # 5. Responsibility language
        if not RESPONSIBILITY_HINTS.search(content):
            score -= 5
            feedback.append(FeedbackItemResult(
                category="Responsibility Distribution",
                severity=Severity.SUGGESTION,
                message="The submission doesn't explicitly discuss responsibilities per class.",
                suggestion="For each class, state the single responsibility it owns.",
            ))

        # 6. Expected concept coverage (matched against the problem's own metadata,
        # not a hidden fixed key — so this scales to any problem without code changes)
        matched_concepts = [c for c in expected_concepts if c.lower() in content.lower()]
        missing_concepts = [c for c in expected_concepts if c not in matched_concepts]
        if expected_concepts:
            coverage = len(matched_concepts) / len(expected_concepts)
            if coverage < 0.5:
                score -= 15
            feedback.append(FeedbackItemResult(
                category="Concept Coverage",
                severity=Severity.INFO if coverage >= 0.5 else Severity.SUGGESTION,
                message=f"Referenced {len(matched_concepts)}/{len(expected_concepts)} of the "
                        f"concepts this problem is designed to exercise: "
                        f"{', '.join(matched_concepts) or 'none'}.",
                suggestion=(f"Consider whether {', '.join(missing_concepts)} apply to your design."
                            if missing_concepts else None),
            ))

        # 7. Trade-off / extensibility discussion presence (structural only —
        # the LLM evaluator judges whether the reasoning is actually good)
        if not TRADEOFF_HINTS.search(content) and not EXTENSIBILITY_HINTS.search(content):
            score -= 10
            feedback.append(FeedbackItemResult(
                category="Extensibility & Trade-offs",
                severity=Severity.SUGGESTION,
                message="No trade-off or extensibility discussion detected.",
                suggestion="Briefly note one alternative you considered and why you didn't "
                           "pick it, or how the design would accommodate a new requirement.",
            ))

        score = max(0, min(100, score))
        summary = (
            f"Deterministic structural check: {len(class_matches)} class(es)/interface(s), "
            f"{len(matched_concepts) if expected_concepts else 0}/{len(expected_concepts)} "
            f"expected concept(s) referenced, {word_count} words."
        )
        return EvaluationResult(
            evaluator_type="DETERMINISTIC",
            score=score,
            summary=summary,
            feedback_items=feedback,
        )
