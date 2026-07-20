from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceRead(BaseModel):
    """Output schema — what the API returns for one uploaded evidence photo."""

    id: str
    claim_id: str
    file_name: str
    file_url: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
