from app.evaluation.deterministic import DeterministicEvaluator


def _run(content, expected_concepts=None):
    ev = DeterministicEvaluator()
    return ev.evaluate(
        submission_content=content,
        submission_format="TEXT",
        problem_summary="Design a parking lot.",
        requirements=["Support multiple vehicle types"],
        constraints=["Motorcycles fit any spot"],
        expected_concepts=expected_concepts or ["Strategy", "Factory"],
    )


def test_empty_like_submission_scores_low():
    result = _run("not much here")
    assert result.score < 50
    assert any(f.category == "Completeness" for f in result.feedback_items)


def test_well_structured_submission_scores_higher_than_placeholder():
    good = """
    class ParkingLot {
        responsibility: coordinates spot assignment across floors
    }
    interface PricingStrategy {
        calculateFee(duration): number
    }
    class HourlyPricingStrategy implements PricingStrategy {
        responsibility: computes fee per hour
    }
    ParkingLot has-a composition relationship with ParkingSpot.
    We considered a single God class instead but rejected it as a trade-off
    since it would not be extensible for new vehicle types via a Factory.
    """
    result = _run(good)
    placeholder = _run("just a placeholder")
    assert result.score > placeholder.score
    assert result.score >= 70


def test_god_object_smell_detected():
    god_object = "class Everything { " + "responsibility " * 40 + " }"
    result = _run(god_object)
    categories = [f.category for f in result.feedback_items]
    assert "Responsibility Distribution" in categories


def test_concept_coverage_matches_problem_metadata():
    content = "class X { } We used the Strategy pattern for pricing."
    result = _run(content, expected_concepts=["Strategy", "Observer"])
    coverage_item = next(f for f in result.feedback_items if f.category == "Concept Coverage")
    assert "Strategy" in coverage_item.message
    assert "1/2" in coverage_item.message


def test_score_always_within_bounds():
    result = _run("")
    assert 0 <= result.score <= 100
