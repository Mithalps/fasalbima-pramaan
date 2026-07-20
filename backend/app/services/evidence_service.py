import io
import logging
import os
import uuid

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import (
    EvidenceLimitExceededError,
    EvidenceNotFoundError,
    FileTooLargeError,
    InvalidImageError,
    UnsupportedFileTypeError,
)
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceRead
from app.services import claim_service

logger = logging.getLogger("fasalbima.evidence")

# Maps accepted MIME types to a canonical file extension. Only these three
# formats are accepted, per Feature 2's requirements.
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_MAX_FILE_SIZE_BYTES = settings.max_evidence_file_size_mb * 1024 * 1024


def _claim_upload_dir(claim_id: str) -> str:
    """Every claim's evidence photos live in their own subfolder, so files
    from different claims never collide and deleting a claim's evidence is
    a simple directory sweep."""
    path = os.path.join(settings.upload_dir, claim_id)
    os.makedirs(path, exist_ok=True)
    return path


def _to_read_schema(evidence: Evidence) -> EvidenceRead:
    """
    Builds the API-facing schema, adding the browser-servable file_url —
    a field that only exists as a derived value, not a column on the model.
    """
    relative_path = evidence.file_path.replace(os.sep, "/")
    file_url = f"{settings.upload_url_prefix}/{relative_path}"
    return EvidenceRead(
        id=evidence.id,
        claim_id=evidence.claim_id,
        file_name=evidence.file_name,
        file_url=file_url,
        uploaded_at=evidence.uploaded_at,
    )


def _validate_and_read(file: UploadFile, raw_bytes: bytes) -> str:
    """
    Validates content-type, size, and that the bytes are a genuinely
    decodable image (guards against a renamed non-image file slipping
    through on content-type alone). Returns the extension to save with.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError(content_type or "unknown")

    if len(raw_bytes) > _MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(settings.max_evidence_file_size_mb)

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError() from exc

    return _ALLOWED_CONTENT_TYPES[content_type]


async def upload_evidence(db: Session, claim_id: str, file: UploadFile) -> EvidenceRead:
    """
    Validates and stores one evidence photo for a claim.

    Order of checks: claim exists -> under the per-claim image limit ->
    file type/size/content valid. Failing fast on the cheapest checks first
    avoids reading the whole file into memory for a claim that doesn't even
    have room for another image.
    """
    claim_service.get_claim(db, claim_id)  # raises ClaimNotFoundError if missing

    existing_count = db.execute(
        select(Evidence).where(Evidence.claim_id == claim_id)
    ).scalars().all()
    if len(existing_count) >= settings.max_evidence_images_per_claim:
        raise EvidenceLimitExceededError(settings.max_evidence_images_per_claim)

    raw_bytes = await file.read()
    extension = _validate_and_read(file, raw_bytes)

    unique_filename = f"{uuid.uuid4()}{extension}"
    claim_dir = _claim_upload_dir(claim_id)
    absolute_path = os.path.join(claim_dir, unique_filename)

    with open(absolute_path, "wb") as f:
        f.write(raw_bytes)

    relative_path = os.path.join(claim_id, unique_filename)
    evidence = Evidence(
        claim_id=claim_id,
        file_name=file.filename or unique_filename,
        file_path=relative_path,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    logger.info(
        "Evidence uploaded id=%s claim_id=%s file_name=%s size_bytes=%d",
        evidence.id,
        claim_id,
        evidence.file_name,
        len(raw_bytes),
    )
    return _to_read_schema(evidence)


def list_evidence(db: Session, claim_id: str) -> list[EvidenceRead]:
    claim_service.get_claim(db, claim_id)  # raises ClaimNotFoundError if missing

    result = db.execute(
        select(Evidence)
        .where(Evidence.claim_id == claim_id)
        .order_by(Evidence.uploaded_at.asc())
    )
    return [_to_read_schema(item) for item in result.scalars().all()]


def _get_evidence_or_raise(db: Session, evidence_id: str) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise EvidenceNotFoundError(evidence_id)
    return evidence


def delete_evidence(db: Session, evidence_id: str) -> None:
    evidence = _get_evidence_or_raise(db, evidence_id)

    absolute_path = os.path.join(settings.upload_dir, evidence.file_path)
    if os.path.exists(absolute_path):
        os.remove(absolute_path)
    else:
        logger.warning("Evidence file missing on disk id=%s path=%s", evidence_id, absolute_path)

    db.delete(evidence)
    db.commit()
    logger.info("Evidence deleted id=%s", evidence_id)


def delete_all_files_for_claim(db: Session, claim_id: str) -> None:
    """
    Removes evidence files from disk for a claim that's about to be deleted.
    The Evidence *rows* are removed automatically by the ORM cascade on
    Claim (cascade="all, delete-orphan") — this only handles the files,
    which SQLAlchemy has no knowledge of.
    """
    result = db.execute(select(Evidence).where(Evidence.claim_id == claim_id))
    for evidence in result.scalars().all():
        absolute_path = os.path.join(settings.upload_dir, evidence.file_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
