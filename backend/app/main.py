from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

app = FastAPI(
    title=settings.app_name,
    description="Backend API for FasalBima Pramaan — voice-guided PMFBY crop-damage claim evidence assistant.",
    version="0.1.0",
)

# Only the frontend's dev origin may call this API from a browser.
# Add production origins to this list once the frontend is deployed (Module 14).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """
    Confirms the full backend chain is working:
      - the FastAPI process is up
      - the SQLAlchemy engine can open a real SQLite connection
      - a real query executes against it (not just "the file exists")

    This is what Module 1 is graded on — everything after this is
    built in later modules.
    """
    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "database": "connected",
    }


@app.get("/")
def root():
    return {
        "message": "FasalBima Pramaan API is running. See /docs for the interactive API explorer."
    }
