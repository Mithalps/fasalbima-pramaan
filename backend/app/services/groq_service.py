import logging

import httpx

from app.config import settings
from app.exceptions import GroqCredentialsMissingError, GroqServiceError, GroqTimeoutError

logger = logging.getLogger("fasalbima.groq")

_GROQ_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

_FORMAT_TO_FILENAME = {
    "wav": "recording.wav",
    "mp3": "recording.mp3",
    "m4a": "recording.m4a",
    "webm": "recording.webm",
    "ogg": "recording.ogg",
}

_FORMAT_TO_MIME = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "webm": "audio/webm",
    "ogg": "audio/ogg",
}


def _credentials_present() -> bool:
    return bool(settings.groq_api_key)


async def transcribe(
    audio_bytes: bytes,
    audio_format: str,
    language: str | None = None,
) -> str:
    """
    Transcribe audio using Groq's OpenAI-compatible Whisper API.

    audio_format is one of wav, mp3, m4a, webm, ogg — not a MIME type.
    """
    if not _credentials_present():
        raise GroqCredentialsMissingError()

    filename = _FORMAT_TO_FILENAME.get(audio_format, f"recording.{audio_format}")
    mime = _FORMAT_TO_MIME.get(audio_format, "application/octet-stream")

    form_data = {
        "model": settings.groq_whisper_model,
        "response_format": "json",
    }
    if language:
        form_data["language"] = language

    files = {
        "file": (filename, audio_bytes, mime),
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.groq_request_timeout_seconds) as client:
            response = await client.post(
                _GROQ_TRANSCRIPTIONS_URL,
                data=form_data,
                files=files,
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise GroqTimeoutError() from exc
    except httpx.RequestError as exc:
        raise GroqServiceError(str(exc)) from exc

    if response.status_code != 200:
        raise GroqServiceError(f"HTTP {response.status_code}: {response.text[:300]}")

    try:
        body = response.json()
        transcript = body["text"].strip()
    except (KeyError, ValueError, AttributeError) as exc:
        raise GroqServiceError(f"Unexpected response shape: {exc}") from exc

    logger.info(
        "Groq transcription completed format=%s size_bytes=%d transcript_len=%d",
        audio_format,
        len(audio_bytes),
        len(transcript),
    )
    return transcript
