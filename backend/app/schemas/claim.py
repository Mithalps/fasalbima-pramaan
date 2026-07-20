from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.claim import DamageType, ClaimStatus
from app.schemas.farmer import FarmerCreate, FarmerRead


class ClaimCreate(BaseModel):
    """
    Input schema for POST /api/claims.

    Captures all three form steps (farmer, crop, damage) in a single
    submission, matching the actual user journey: the farmer fills the
    whole guided flow, then submits once at the end.
    """

    farmer: FarmerCreate
    crop_type: str
    damage_type: DamageType
    damage_date: date
    district: str
    village: str

    @field_validator("crop_type", "district", "village")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("This field must be at least 2 characters long")
        return value

    @field_validator("damage_date")
    @classmethod
    def damage_date_cannot_be_in_the_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Damage date cannot be in the future")
        return value


class ClaimUpdate(BaseModel):
    """
    Input schema for PUT /api/claims/{id}.

    Every field is optional: the caller sends only what changed. This is a
    partial update (PATCH semantics under a PUT verb, which is acceptable
    here since the whole resource is still addressed by the same URL and
    every field keeps its previous value when omitted).
    """

    crop_type: str | None = None
    damage_type: DamageType | None = None
    damage_date: date | None = None
    district: str | None = None
    village: str | None = None
    status: ClaimStatus | None = None

    @field_validator("crop_type", "district", "village")
    @classmethod
    def must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) < 2:
            raise ValueError("This field must be at least 2 characters long")
        return value

    @field_validator("damage_date")
    @classmethod
    def damage_date_cannot_be_in_the_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Damage date cannot be in the future")
        return value


class ClaimRead(BaseModel):
    """Output schema — the full claim, with the farmer nested inline."""

    claim_id: str
    farmer: FarmerRead
    crop_type: str
    damage_type: DamageType
    damage_date: date
    district: str
    village: str
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
