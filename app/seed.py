from sqlalchemy.orm import Session

from app.models import Problem, Difficulty

PROBLEMS = [
    dict(
        title="Parking Lot System",
        difficulty=Difficulty.MEDIUM,
        summary=(
            "Design a parking lot that supports multiple vehicle types (motorcycle, car, "
            "bus), multiple spot sizes, and computes a parking fee when a vehicle exits."
        ),
        requirements=[
            "Support at least 3 vehicle types with different spot-size needs",
            "Assign the smallest suitable free spot to an entering vehicle",
            "Track entry/exit time and compute a fee on exit",
            "Support multiple floors/levels",
        ],
        constraints=[
            "A motorcycle can park in any spot size; a bus needs a large spot",
            "Pricing may vary by vehicle type and duration",
        ],
        expected_concepts=["Strategy", "Factory", "Single Responsibility"],
    ),
    dict(
        title="Elevator Control System",
        difficulty=Difficulty.HARD,
        summary=(
            "Design the control logic for a bank of elevators in a building, handling "
            "external hall calls and internal cabin requests efficiently."
        ),
        requirements=[
            "Handle simultaneous requests from multiple floors",
            "Decide which elevator should service a new request",
            "Support direction (up/down) and stop scheduling per elevator",
            "Be extensible to different dispatch algorithms",
        ],
        constraints=[
            "An elevator should not reverse direction while requests remain in its current direction",
            "Multiple elevators can exist in the same system",
        ],
        expected_concepts=["State", "Strategy", "Observer"],
    ),
    dict(
        title="Vending Machine",
        difficulty=Difficulty.EASY,
        summary=(
            "Design a vending machine that accepts coins/notes, lets a user select a "
            "product, dispenses it, and returns change, modeled as an explicit state machine."
        ),
        requirements=[
            "Model machine states (idle, has-money, dispensing, out-of-stock)",
            "Support selecting a product and validating sufficient payment",
            "Compute and dispense change",
            "Track per-slot inventory",
        ],
        constraints=[
            "The machine must reject selection if the slot is empty",
            "The machine must not dispense if payment is insufficient",
        ],
        expected_concepts=["State", "Encapsulation"],
    ),
    dict(
        title="Library Management System",
        difficulty=Difficulty.MEDIUM,
        summary=(
            "Design a system for a library to manage books, members, borrowing, returning, "
            "and reservation of currently-borrowed books."
        ),
        requirements=[
            "Support searching the catalog by title/author",
            "Support borrowing and returning a book with due dates",
            "Support reserving a book that is currently checked out",
            "Support late-fee calculation",
        ],
        constraints=[
            "A member has a maximum number of books they may borrow at once",
            "A reserved book should be held for the reserving member when returned",
        ],
        expected_concepts=["Observer", "Repository", "Single Responsibility"],
    ),
]


def seed_problems(db: Session) -> None:
    if db.query(Problem).count() > 0:
        return
    for p in PROBLEMS:
        db.add(Problem(**p))
    db.commit()
