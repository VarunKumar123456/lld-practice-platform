import time
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_lld_practice.db")

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # Startup events (table creation + seeding) only fire inside the
    # context manager, so every test in this module shares one client.
    with TestClient(app) as c:
        yield c
    try:
        os.remove("./test_lld_practice.db")
    except FileNotFoundError:
        pass


def test_list_problems_returns_seeded_set(client):
    res = client.get("/api/problems")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
    titles = [p["title"] for p in data]
    assert "Parking Lot System" in titles


def test_get_single_problem(client):
    problem_id = client.get("/api/problems").json()[0]["id"]
    res = client.get(f"/api/problems/{problem_id}")
    assert res.status_code == 200
    assert "requirements" in res.json()


def test_unknown_problem_returns_404(client):
    res = client.get("/api/problems/does-not-exist")
    assert res.status_code == 404


def test_full_practice_loop_choose_design_submit_feedback_history(client):
    problem = client.get("/api/problems").json()[0]

    # Choose + start attempt
    attempt = client.post("/api/attempts", json={
        "problem_id": problem["id"], "learner_id": "test-learner",
    }).json()
    assert attempt["status"] == "IN_PROGRESS"

    # Design + Submit
    submission = client.post(f"/api/attempts/{attempt['id']}/submissions", json={
        "format": "CODE",
        "content": "class ParkingLot { responsibility: assigns spots } "
                   "interface PricingStrategy { calculateFee() } "
                   "class HourlyPricingStrategy implements PricingStrategy { }",
    }).json()
    assert submission["status"] in ("PENDING", "EVALUATING", "COMPLETED")

    # Feedback: poll until evaluation completes (background task)
    for _ in range(20):
        sub = client.get(
            f"/api/attempts/{attempt['id']}/submissions/{submission['id']}"
        ).json()
        if sub["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.2)
    assert sub["status"] == "COMPLETED"
    assert len(sub["evaluations"]) == 2  # deterministic + llm
    evaluator_types = {e["evaluator_type"] for e in sub["evaluations"]}
    assert evaluator_types == {"DETERMINISTIC", "LLM"}

    # Review / History
    history = client.get("/api/history/test-learner").json()
    assert len(history) == 1
    assert history[0]["submissions"][0]["id"] == submission["id"]


def test_resubmission_increments_attempt_number(client):
    problem = client.get("/api/problems").json()[1]
    attempt = client.post("/api/attempts", json={
        "problem_id": problem["id"], "learner_id": "test-learner-2",
    }).json()

    s1 = client.post(f"/api/attempts/{attempt['id']}/submissions", json={
        "format": "TEXT", "content": "first pass, very short",
    }).json()
    s2 = client.post(f"/api/attempts/{attempt['id']}/submissions", json={
        "format": "TEXT", "content": "second, improved pass with more detail",
    }).json()
    assert s1["attempt_number"] == 1
    assert s2["attempt_number"] == 2


def test_empty_submission_content_rejected(client):
    problem = client.get("/api/problems").json()[0]
    attempt = client.post("/api/attempts", json={
        "problem_id": problem["id"], "learner_id": "test-learner-3",
    }).json()
    res = client.post(f"/api/attempts/{attempt['id']}/submissions", json={
        "format": "TEXT", "content": "",
    })
    assert res.status_code == 422


def test_submission_to_nonexistent_attempt_returns_404(client):
    res = client.post("/api/attempts/does-not-exist/submissions", json={
        "format": "TEXT", "content": "something",
    })
    assert res.status_code == 404
