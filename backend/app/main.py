import logging
import os

from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, Base, engine

# Importing app.models registers Farmer, Claim, and Evidence with Base's
# metadata. This import must happen before Base.metadata.create_all() below,
# or create_all() would run with no tables to create.
import app.models  # noqa: F401
from app.routers import claims
from app.routers.evidence import claims_router as evidence_claims_router
from app.routers.evidence import evidence_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("fasalbima")

app = FastAPI(
    title=settings.app_name,
    description="Backend API for FasalBima Pramaan — voice-guided PMFBY crop-damage claim evidence assistant.",
    version="0.2.0",
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


@app.on_event("startup")
def on_startup():
    """
    Creates any tables that don't exist yet. Fine for this project's scope;
    a production system with evolving schemas would use Alembic migrations
    instead of create_all (see MODULE_2.md, Known Limitations).
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")

    # Feature 2: make sure the evidence-photo upload directory exists.
    # SQLite creates its own file, but the filesystem won't create this
    # folder on its own.
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info("Upload directory verified/created at %s", settings.upload_dir)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches anything that isn't already a handled HTTPException, so a bug
    in a later module returns a clean 500 with a JSON body instead of an
    unformatted stack trace — while the real traceback still goes to the
    server log for debugging.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


app.include_router(claims.router)
app.include_router(evidence_claims_router)
app.include_router(evidence_router)

# StaticFiles requires its directory to exist at mount time (import time),
# which is earlier than the startup event above — so it's created here too,
# not just in on_startup.
os.makedirs(settings.upload_dir, exist_ok=True)

# Serves uploaded evidence photos at e.g. /uploads/{claim_id}/{file}.jpg so
# the frontend can render thumbnails directly from the file_url the API
# returns.
app.mount(
    settings.upload_url_prefix,
    StaticFiles(directory=settings.upload_dir),
    name="uploads",
)


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """
    Confirms the full backend chain is working:
      - the FastAPI process is up
      - the SQLAlchemy engine can open a real SQLite connection
      - a real query executes against it (not just "the file exists")
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

