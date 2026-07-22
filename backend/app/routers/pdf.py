"""
app/routers/pdf.py
===================
Download endpoint for the generated claim-evidence PDF.

Mount in main.py alongside the existing routers, e.g.:

    from app.routers.pdf import router as pdf_router
    app.include_router(pdf_router)
"""

import io
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.exceptions import ClaimNotFoundError
from app.models.claim import Claim
from app.services.pdf_service import generate_claim_pdf

logger = logging.getLogger("fasalbima.pdf.router")

router = APIRouter(prefix="/api/claims", tags=["pdf"])


def _get_claim_with_relations(db: Session, claim_id: str) -> Claim:
    claim = (
        db.query(Claim)
        .options(
            joinedload(Claim.farmer),
            joinedload(Claim.evidence_items),
        )
        .filter(Claim.claim_id == claim_id)
        .first()
    )
    if claim is None:
        raise ClaimNotFoundError(claim_id)
    return claim


@router.get(
    "/{claim_id}/pdf",
    summary="Download the evidence PDF for a claim",
    response_class=StreamingResponse,
)
def download_claim_pdf(claim_id: str, db: Session = Depends(get_db)):
    try:
        claim = _get_claim_with_relations(db, claim_id)
    except ClaimNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        pdf_bytes = generate_claim_pdf(claim)
    except Exception:
        logger.exception("PDF generation failed for claim_id=%s", claim_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate claim PDF.",
        )

    filename = f"fasalbima_claim_{claim_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
