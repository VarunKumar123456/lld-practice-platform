from app.evaluation.llm_evaluator import HeuristicLLMEvaluator, build_llm_evaluator
import os


def test_heuristic_flags_singleton():
    ev = HeuristicLLMEvaluator()
    result = ev.evaluate(
        submission_content="class Inventory { } // implemented as a Singleton for global access",
        submission_format="TEXT",
        problem_summary="Design a vending machine.",
        requirements=[], constraints=[], expected_concepts=[],
    )
    assert any(f.category == "Coupling" for f in result.feedback_items)


def test_heuristic_never_raises_on_empty_content():
    ev = HeuristicLLMEvaluator()
    result = ev.evaluate(
        submission_content="",
        submission_format="TEXT",
        problem_summary="x", requirements=[], constraints=[], expected_concepts=[],
    )
    assert result.feedback_items  # always returns something demoable


def test_factory_falls_back_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ev = build_llm_evaluator()
    assert isinstance(ev, HeuristicLLMEvaluator)
