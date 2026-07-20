import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

_MOBILE_PATTERN = re.compile(r"^[6-9]\d{9}$")


class FarmerCreate(BaseModel):
    """Input schema for the farmer details captured in Step 1 of the claim form."""

    farmer_name: str
    mobile_number: str

    @field_validator("farmer_name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Farmer name must be at least 2 characters long")
        return value

    @field_validator("mobile_number")
    @classmethod
    def mobile_must_be_valid_indian_number(cls, value: str) -> str:
        value = value.strip()
        if not _MOBILE_PATTERN.match(value):
            raise ValueError(
                "Mobile number must be a 10-digit Indian mobile number starting with 6-9"
            )
        return value


class FarmerRead(BaseModel):
    """Output schema — what the API returns for a farmer, nested inside a claim."""

    farmer_id: str
    farmer_name: str
    mobile_number: str
    created_at: datetime

    # Lets Pydantic build this schema directly from a SQLAlchemy ORM object
    # (Farmer model instance) instead of requiring a dict.
    model_config = ConfigDict(from_attributes=True)
