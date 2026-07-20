import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import ClaimNotFoundError
from app.schemas.claim import ClaimCreate, ClaimUpdate, ClaimRead
from app.services import claim_service

logger = logging.getLogger("fasalbima.claims.router")

router = APIRouter(prefix="/api/claims", tags=["claims"])


@router.post(
    "",
    response_model=ClaimRead,
    status_code=status.HTTP_201_CREATED,
    summary="File a new crop-damage claim",
)
def create_claim(payload: ClaimCreate, db: Session = Depends(get_db)):
    """
    Creates the farmer record (or reuses an existing one matched by mobile
    number) and the claim in a single request — this is the endpoint the
    "Submit" button on the final review screen calls.
    """
    claim = claim_service.create_claim(db, payload)
    return claim


@router.get(
    "",
    response_model=list[ClaimRead],
    summary="List claims",
)
def list_claims(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Returns claims newest-first. skip/limit provide basic pagination."""
    return claim_service.list_claims(db, skip=skip, limit=limit)


@router.get(
    "/{claim_id}",
    response_model=ClaimRead,
    summary="Get a single claim by ID",
)
def get_claim(claim_id: str, db: Session = Depends(get_db)):
    try:
        return claim_service.get_claim(db, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.put(
    "/{claim_id}",
    response_model=ClaimRead,
    summary="Update a claim",
)
def update_claim(claim_id: str, payload: ClaimUpdate, db: Session = Depends(get_db)):
    try:
        return claim_service.update_claim(db, claim_id, payload)
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete(
    "/{claim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a claim",
)
def delete_claim(claim_id: str, db: Session = Depends(get_db)):
    try:
        claim_service.delete_claim(db, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
