import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import (
    ClaimNotFoundError,
    EvidenceLimitExceededError,
    EvidenceNotFoundError,
    FileTooLargeError,
    InvalidImageError,
    UnsupportedFileTypeError,
)
from app.schemas.evidence import EvidenceRead
from app.services import evidence_service

logger = logging.getLogger("fasalbima.evidence.router")

# Mounted under /api/claims so the claim-scoped routes (upload, list) sit
# next to the existing claims router; the delete-by-id route below is
# registered under a separate prefix since it isn't claim-scoped.
claims_router = APIRouter(prefix="/api/claims", tags=["evidence"])
evidence_router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@claims_router.post(
    "/{claim_id}/evidence",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload one evidence photo for a claim",
)
async def upload_evidence(
    claim_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accepts one JPEG/PNG/WEBP image (max 10MB) at a time — the frontend
    calls this once per selected file so it can show independent progress
    and per-file errors. A claim may hold at most 5 evidence images.
    """
    try:
        return await evidence_service.upload_evidence(db, claim_id, file)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EvidenceLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@claims_router.get(
    "/{claim_id}/evidence",
    response_model=list[EvidenceRead],
    summary="List evidence photos for a claim",
)
def list_evidence(claim_id: str, db: Session = Depends(get_db)):
    try:
        return evidence_service.list_evidence(db, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@evidence_router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an evidence photo",
)
def delete_evidence(evidence_id: str, db: Session = Depends(get_db)):
    try:
        evidence_service.delete_evidence(db, evidence_id)
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
