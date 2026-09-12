# LLD Practice Platform

A focused prototype of a Low-Level Design practice loop: choose a problem,
write a design, submit it, get structural + judgment-based feedback, and
try again with a full attempt history.

See also:
- [`docs/research-note.md`](docs/research-note.md) — learner problem, existing approaches, gaps, product direction.
- [`docs/design-note.md`](docs/design-note.md) — MVP scope, domain model, evaluation approach, trade-offs.
- [`AI_USAGE.md`](AI_USAGE.md) — meaningful AI-assisted decisions during this build.

## Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite (monolith, no auth — see design note §6 for why)
- **Frontend**: a single-file vanilla HTML/JS SPA (no build step) served by the same FastAPI app
- **Evaluation**: a deterministic rule-based evaluator + a pluggable LLM evaluator (real Claude call if `ANTHROPIC_API_KEY` is set, otherwise an offline heuristic fallback — the app works either way)
- **Tests**: pytest — evaluator unit tests + full API integration tests of the practice loop

## Project layout

backend/
app/
main.py # FastAPI app, mounts routers + serves the frontend
database.py # SQLAlchemy engine/session
models.py # Domain model (Problem/Attempt/Submission/Evaluation/FeedbackItem)
schemas.py # Pydantic request/response models
seed.py # Seeds 4 starter problems on first run
routers/
problems.py # GET /api/problems, GET /api/problems/{id}
attempts.py # POST /api/attempts, POST/GET .../submissions
history.py # GET /api/history/{learner_id}
evaluation/
base.py # Evaluator interface (Strategy pattern) + result types
deterministic.py # Rule-based structural evaluator
llm_evaluator.py # Claude-backed evaluator + offline heuristic fallback
pipeline.py # Orchestrates evaluators, handles partial/failed runs
tests/
test_deterministic_evaluator.py
test_llm_evaluator.py
test_api_integration.py
requirements.txt
frontend/
index.html # The whole UI (practice loop, feedback view, history view)
docs/
research-note.md
design-note.md
AI_USAGE.md


## Running it locally

Requires Python 3.11+.

```bash
cd backend
pip install -r requirements.txt   # add --break-system-packages if your pip requires it
python -m uvicorn app.main:app --reload --port 8000
```

Then open **http://localhost:8000/** — the frontend is served directly by
the backend, so there is nothing separate to start.

The SQLite database (`lld_practice.db`) and its 4 seed problems (Parking
Lot, Elevator, Vending Machine, Library) are created automatically on
first startup.

### Using a real LLM for the "judgment" evaluator (optional)

By default, the LLM evaluator runs a deterministic offline fallback so the
whole app works out of the box with zero configuration. To get real model
reasoning instead:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# optional, defaults to claude-sonnet-4-6
export ANTHROPIC_MODEL=claude-sonnet-4-6
python -m uvicorn app.main:app --reload --port 8000
```

### Running the tests

```bash
cd backend
python -m pytest tests/ -v
```

15 tests covering: deterministic evaluator behaviour (completeness, God
Object smell, concept coverage), the offline LLM fallback, and full API
integration tests of the practice loop (start attempt → submit →
poll-until-evaluated → resubmit → history), plus edge cases (empty
content rejected, unknown problem/attempt returns 404).

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/problems` | List problems |
| GET | `/api/problems/{id}` | Problem detail (requirements/constraints/concepts) |
| POST | `/api/attempts` | Start an attempt on a problem |
| POST | `/api/attempts/{id}/submissions` | Submit a solution (kicks off background evaluation) |
| GET | `/api/attempts/{id}/submissions/{sub_id}` | Poll a submission's status + evaluations |
| GET | `/api/history/{learner_id}` | All attempts + submissions for a learner |

## Known limitations (2-day MVP scope)

- No authentication — `learner_id` is a free-form string, defaulted to
  `"demo-learner"` by the frontend.
- No DIAGRAM-format rendering — diagram submissions are accepted as text
  (e.g. a Mermaid-like description) and evaluated the same way as TEXT;
  actual diagram parsing/rendering is out of scope for 2 days.
- Evaluation runs in-process via a FastAPI `BackgroundTask`, not a real job
  queue — sufficient at this scale; see design note §5 for how this would
  extend to a queue-based worker if needed.
- No pagination on `/api/history` — fine at demo scale, would need it for
  a learner with hundreds of attempts.
