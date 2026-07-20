from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    """Response body for POST /api/speech/transcribe."""

    success: bool
    transcript: str
