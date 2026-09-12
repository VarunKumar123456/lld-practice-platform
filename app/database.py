"""
Database engine/session setup.

We use SQLite for the prototype (zero-config, file-based) but all access goes
through SQLAlchemy's ORM, so swapping to Postgres later is a one-line change
to DATABASE_URL plus a driver swap — nothing in the domain/service layer
needs to know which database is behind it.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lld_practice.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
