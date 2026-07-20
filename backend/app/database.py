import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Make sure the folder that will hold the SQLite file actually exists.
# (SQLite will happily create the .db file itself, but not the directory.)
db_path = settings.database_url.replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

# check_same_thread=False is required for SQLite when it's accessed from
# FastAPI's threaded request handling; SQLAlchemy's session handling keeps
# this safe for our single-writer, request-scoped usage pattern.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base that every ORM model (added starting in Module 2) inherits from
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a database session for a single request
    and guarantees it is closed afterwards, even if the request raises.

    Usage in a route:
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
