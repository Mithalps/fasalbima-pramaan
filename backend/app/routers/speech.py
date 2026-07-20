import logging

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from app.exceptions import SpeechServiceError
from app.schemas.speech import TranscribeResponse
from app.services import speech_service

logger = logging.getLogger("fasalbima.speech.router")

router = APIRouter(prefix="/api/speech", tags=["speech"])


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe a voice recording (Kannada by default) to text",
)
async def transcribe(
    audio: UploadFile,
    language: str | None = Form(default=None),
):
    """
    Accepts an audio recording (wav, mp3, m4a, webm, or ogg) and returns its
    transcript using Groq's hosted Whisper Large v3. This is the endpoint
    the microphone button on the claim form calls.
    """
    audio_bytes = await audio.read()

    logger.info(
        "Received transcription request filename=%s content_type=%s size_bytes=%d",
        audio.filename,
        audio.content_type,
        len(audio_bytes),
    )

    try:
        speech_service.validate_audio_upload(
            content_type=audio.content_type, size_bytes=len(audio_bytes)
        )
        transcript = speech_service.transcribe_audio(
            file_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
            language=language,
        )
    except SpeechServiceError as exc:
        logger.warning(
            "Transcription request failed filename=%s reason=%s",
            audio.filename,
            exc.message,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return TranscribeResponse(success=True, transcript=transcript)
