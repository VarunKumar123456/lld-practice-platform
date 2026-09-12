"""
LLM evaluator.

Design principle (answers "which parts benefit from an LLM?"):

The LLM is used ONLY for judgment calls that don't have a single right
answer — the things the deterministic evaluator explicitly cannot check:
  - Is the chosen abstraction actually a *good* fit for the problem, or
    just present?
  - Is the stated trade-off reasoning sound, not just "a trade-offs section
    exists"?
  - Qualitative, human-readable feedback in the learner's own design
    vocabulary ("why this hurts you later"), which is what makes feedback
    feel useful rather than a lint report.

It deliberately does NOT re-do what the deterministic evaluator already
does (existence checks, keyword coverage) — that would waste a call and
make the two evaluators disagree over facts rather than judgment.

Two implementations behind the same `Evaluator` interface (Strategy
pattern, matches base.py):
  - ClaudeLLMEvaluator: calls the real Anthropic API (used when
    ANTHROPIC_API_KEY is set).
  - HeuristicLLMEvaluator: a deterministic *stand-in* used when no API key
    is configured, so the prototype is fully demoable offline / in CI
    without secrets. It is clearly labeled as a fallback in its output —
    it does not pretend to be a real model's reasoning.

`build_llm_evaluator()` picks the right one at startup. Swapping in a
different provider later (OpenAI, Gemini) means adding one more class here
and one branch in that factory function — nothing else in the app changes.
"""
import os
import json
from typing import List, Optional

from app.evaluation.base import Evaluator, EvaluationResult, FeedbackItemResult
from app.models import Severity

PROMPT_TEMPLATE = """You are an experienced Low-Level Design (LLD) reviewer. \
There can be more than one valid design for this problem — do not penalize a \
learner for choosing a different valid abstraction than you would have. \
Focus ONLY on judgment calls: is the chosen abstraction well-suited to the \
requirements, is the reasoning about trade-offs sound, and is anything \
fragile or hard to extend.

Problem: {problem_summary}
Requirements: {requirements}
Constraints: {constraints}

Learner's submission ({submission_format}):
---
{submission_content}
---

Respond ONLY with JSON, no markdown fences, matching exactly:
{{
  "score": <integer 0-100, your qualitative judgment of design quality>,
  "summary": "<one sentence overall verdict>",
  "feedback_items": [
    {{"category": "<short category>", "severity": "INFO|SUGGESTION|ISSUE|CRITICAL",
      "message": "<specific observation>", "suggestion": "<concrete next step or null>"}}
  ]
}}
Return 2-5 feedback_items, each about a genuine judgment call, not a
presence/absence fact a linter could catch."""


class ClaudeLLMEvaluator(Evaluator):
    name = "llm-claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model = model

    def evaluate(self, *, submission_content, submission_format, problem_summary,
                 requirements, constraints, expected_concepts) -> EvaluationResult:
        try:
            import anthropic
        except ImportError:
            return _fallback_result(
                "The 'anthropic' package is not installed; install it or unset "
                "ANTHROPIC_API_KEY to use the offline heuristic evaluator.")

        client = anthropic.Anthropic(api_key=self.api_key)
        prompt = PROMPT_TEMPLATE.format(
            problem_summary=problem_summary,
            requirements="; ".join(requirements),
            constraints="; ".join(constraints),
            submission_format=submission_format,
            submission_content=submission_content,
        )
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
            data = json.loads(raw.strip().strip("`").removeprefix("json").strip())
            items = [
                FeedbackItemResult(
                    category=i.get("category", "General"),
                    severity=Severity(i.get("severity", "SUGGESTION")),
                    message=i.get("message", ""),
                    suggestion=i.get("suggestion"),
                )
                for i in data.get("feedback_items", [])
            ]
            return EvaluationResult(
                evaluator_type="LLM",
                score=int(data.get("score", 50)),
                summary=data.get("summary", ""),
                feedback_items=items,
            )
        except Exception as exc:  # noqa: BLE001 - evaluation failure must not crash the request
            return _fallback_result(f"LLM call failed ({exc.__class__.__name__}); "
                                     f"showing heuristic feedback instead.")


class HeuristicLLMEvaluator(Evaluator):
    """
    Offline stand-in used when no ANTHROPIC_API_KEY is configured. It looks
    for judgment-flavoured signals (hedging language, single-alternative
    trade-offs, coupling language) so the pipeline and API always have a
    second, qualitative-flavoured opinion to show — the UI and data model
    don't need to special-case "no LLM configured".
    """
    name = "llm-heuristic-fallback"

    def evaluate(self, *, submission_content, submission_format, problem_summary,
                 requirements, constraints, expected_concepts) -> EvaluationResult:
        content_lower = submission_content.lower()
        feedback: List[FeedbackItemResult] = []

        if "interface" in content_lower and "implements" not in content_lower:
            feedback.append(FeedbackItemResult(
                category="Abstraction Quality",
                severity=Severity.SUGGESTION,
                message="An interface is declared but no concrete class is shown implementing "
                        "it — it's unclear whether the abstraction is actually exercised.",
                suggestion="Show at least one concrete implementation to confirm the interface "
                           "earns its place.",
            ))
        if "trade-off" not in content_lower and "tradeoff" not in content_lower:
            feedback.append(FeedbackItemResult(
                category="Reasoning Depth",
                severity=Severity.SUGGESTION,
                message="The submission states a design but doesn't compare it against an "
                        "alternative, so it's hard to judge whether the choice was deliberate.",
                suggestion="Add one sentence on an alternative you rejected and why.",
            ))
        if "singleton" in content_lower:
            feedback.append(FeedbackItemResult(
                category="Coupling",
                severity=Severity.ISSUE,
                message="Singleton is used — this often hides global mutable state and can "
                        "make testing harder; worth a one-line justification.",
                suggestion="Confirm this is intentional (e.g. for a shared inventory/registry) "
                           "rather than a convenience default.",
            ))
        if not feedback:
            feedback.append(FeedbackItemResult(
                category="General",
                severity=Severity.INFO,
                message="No obvious judgment-level concerns found by the offline heuristic "
                        "reviewer; a configured LLM would give deeper, submission-specific "
                        "reasoning.",
            ))

        feedback.append(FeedbackItemResult(
            category="Evaluator Note",
            severity=Severity.INFO,
            message="This feedback came from the offline heuristic fallback because "
                    "ANTHROPIC_API_KEY is not set — set it to get real model reasoning "
                    "instead of pattern-matched hints.",
        ))

        return EvaluationResult(
            evaluator_type="LLM",
            score=None,  # the heuristic fallback deliberately doesn't claim a qualitative score
            summary="Offline heuristic review (no LLM configured) — pattern-matched judgment "
                    "signals only.",
            feedback_items=feedback,
        )


def _fallback_result(reason: str) -> EvaluationResult:
    return EvaluationResult(
        evaluator_type="LLM",
        score=None,
        summary="LLM evaluation unavailable.",
        feedback_items=[FeedbackItemResult(
            category="Evaluator Note", severity=Severity.INFO, message=reason,
        )],
    )


def build_llm_evaluator() -> Evaluator:
    """Factory: picks the real Claude evaluator if a key is configured, else the offline one."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return ClaudeLLMEvaluator(api_key=api_key, model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"))
    return HeuristicLLMEvaluator()
