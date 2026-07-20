import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(Base):
    """
    One uploaded crop-damage photo attached to a claim.

    The actual image bytes live on disk under settings.upload_dir; this row
    only stores metadata. file_name is the original filename the farmer's
    device sent (for display); file_path is the on-disk path used to derive
    the served URL and to delete the file when the evidence row is deleted.
    """

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.claim_id"), nullable=False, index=True
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    claim: Mapped["Claim"] = relationship("Claim", back_populates="evidence_items")
