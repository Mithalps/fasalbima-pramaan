import enum
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DamageType(str, enum.Enum):
    """
    Constrained to the damage scenarios PMFBY's individual-claim window
    actually covers. Kept as an enum (not free text) so invalid values are
    rejected at the database layer, not just the API layer, and so Swagger
    renders this as a dropdown rather than a free-text box.
    """

    FLOOD = "flood"
    DROUGHT = "drought"
    HAILSTORM = "hailstorm"
    PEST_ATTACK = "pest_attack"
    OTHER = "other"


class ClaimStatus(str, enum.Enum):
    """
    Claim lifecycle status. Feature 1 only ever sets SUBMITTED on creation;
    the remaining values exist so the schema doesn't need to change when
    later features (surveyor review, evidence packet ready) start using them.
    """

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    EVIDENCE_READY = "evidence_ready"
    CLOSED = "closed"


class Claim(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    farmer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("farmers.farmer_id"), nullable=False, index=True
    )

    # Free text, not an enum: the proposal's own scalability section notes
    # new crops are added by labeling more images, not by changing code —
    # locking this to an enum would contradict that.
    crop_type: Mapped[str] = mapped_column(String(80), nullable=False)

    damage_type: Mapped[DamageType] = mapped_column(
        SAEnum(DamageType, name="damage_type_enum"), nullable=False
    )
    damage_date: Mapped[date] = mapped_column(Date, nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    village: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[ClaimStatus] = mapped_column(
        SAEnum(ClaimStatus, name="claim_status_enum"),
        default=ClaimStatus.SUBMITTED,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    farmer: Mapped["Farmer"] = relationship("Farmer", back_populates="claims")

    # Feature 2: evidence photos attached to this claim. Deleting a claim
    # deletes its evidence rows too — the actual files are cleaned up in
    # services/claim_service.delete_claim before this cascade runs.
    evidence_items: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="claim", cascade="all, delete-orphan"
    )
