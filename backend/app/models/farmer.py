import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Farmer(Base):
    """
    A farmer who has filed one or more crop-damage claims.

    Farmers are deduplicated by mobile_number in the service layer
    (see services/claim_service.py: get_or_create_farmer) — the same
    farmer filing a second claim does not create a duplicate row.
    """

    __tablename__ = "farmers"

    farmer_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    farmer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    mobile_number: Mapped[str] = mapped_column(
        String(15), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # One farmer can have many claims. cascade="all, delete-orphan" means
    # deleting a farmer would delete their claims too — but Feature 1 never
    # exposes farmer deletion, only claim deletion, so this is a safety net
    # rather than an active code path.
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="farmer", cascade="all, delete-orphan"
    )
