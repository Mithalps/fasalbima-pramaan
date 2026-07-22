import enum
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, Date, DateTime, ForeignKey, Float, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DamageType(str, enum.Enum):
    FLOOD = "flood"
    DROUGHT = "drought"
    HAILSTORM = "hailstorm"
    PEST_ATTACK = "pest_attack"
    OTHER = "other"


class ClaimStatus(str, enum.Enum):
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

    # Module 10: Weather Validation. All nullable — populated after claim
    # creation by an automatic weather-validation call in claim_service.py,
    # and left null if that call fails or isn't applicable to the reported
    # damage_type. Weather validation is corroborating evidence only; it
    # never overrides the farmer-reported damage_type or blocks creation.
    weather_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    weather_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    precipitation: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    windspeed: Mapped[float | None] = mapped_column(Float, nullable=True)

    farmer: Mapped["Farmer"] = relationship("Farmer", back_populates="claims")

    evidence_items: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="claim", cascade="all, delete-orphan"
    )