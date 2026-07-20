from pydantic import BaseModel


class ClassifyResponse(BaseModel):
    """Response body for POST /api/classify."""

    prediction: str
    confidence: float
