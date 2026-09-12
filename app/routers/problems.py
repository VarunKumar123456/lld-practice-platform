from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Problem
from app.schemas import ProblemListItem, ProblemOut

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=List[ProblemListItem])
def list_problems(db: Session = Depends(get_db)):
    return db.query(Problem).all()


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: str, db: Session = Depends(get_db)):
    problem = db.query(Problem).get(problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")
    return problem
