import logging
import time

import groq

from app.config import settings
from app.exceptions import (
    AudioTooLargeError,
    EmptyAudioError,
    MissingAPIKeyError,
    TranscriptionFailedError,
    TranscriptionTimeoutError,
    UnsupportedAudioTypeError,
)

logger = logging.getLogger("fasalbima.speech")

# Groq Whisper (like the OpenAI Whisper API it's compatible with) accepts
# these container formats natively — no client- or server-side transcoding
# is needed for any of them, including the webm/opus that browser
# MediaRecorder typically produces.
SUPPORTED_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/webm",
    "video/webm",  # some browsers label audio-only MediaRecorder blobs this way
    "audio/ogg",
    "application/ogg",
}

_client: groq.Groq | None = None


def _normalize_content_type(content_type: str | None) -> str:
    """Strips parameters like ';codecs=opus' that browsers append to content types."""
    return (content_type or "").split(";")[0].strip().lower()


def validate_audio_upload(content_type: str | None, size_bytes: int) -> None:
    """
    Validates an uploaded audio file before it's sent to Groq. Raises:
      - EmptyAudioError            if size_bytes is 0
      - AudioTooLargeError         if size_bytes exceeds the configured limit
      - UnsupportedAudioTypeError  if content_type isn't one Groq accepts
    """
    if size_bytes == 0:
        raise EmptyAudioError("The recording was empty. Please try again.")

    max_bytes = settings.speech_max_audio_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise AudioTooLargeError(
            f"That recording is too large ({size_bytes / (1024 * 1024):.1f} MB). "
            f"The limit is {settings.speech_max_audio_size_mb} MB."
        )

    normalized = _normalize_content_type(content_type)
    if normalized not in SUPPORTED_AUDIO_MIME_TYPES:
        raise UnsupportedAudioTypeError(
            f"Unsupported audio format ({content_type or 'unknown'}). "
            "Supported formats: wav, mp3, m4a, webm, ogg."
        )



def _get_client() -> groq.Groq:
    """
    Lazily builds the Groq client on first use so a missing API key fails
    loudly with a clear error the first time transcription is attempted,
    rather than crashing the whole app at import time.
    """
    global _client

    if not settings.groq_api_key:
        raise MissingAPIKeyError(
            "Speech transcription isn't configured on this server: "
            "GROQ_API_KEY is missing. Add it to backend/.env and restart."
        )

    if _client is None:
        _client = groq.Groq(api_key=settings.groq_api_key)

    return _client


def transcribe_audio(
    file_bytes: bytes,
    filename: str,
    language: str | None = None,
) -> str:

    """
    Sends audio bytes to Groq's hosted Whisper Large v3 and returns the
    transcript text.

    Raises (all subclasses of SpeechServiceError, see app/exceptions.py):
      - MissingAPIKeyError        if GROQ_API_KEY isn't configured
      - TranscriptionTimeoutError if Groq doesn't respond in time
      - TranscriptionFailedError  for any other Groq-side failure, or an
                                  empty/unusable response
    """
    client = _get_client()
    language = language or settings.speech_default_language

    logger.info(
        "Speech request started filename=%s size_bytes=%d language=%s model=%s",
        filename,
        len(file_bytes),
        language,
        settings.groq_whisper_model,
    )

    start = time.perf_counter()
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, file_bytes),
            model=settings.groq_whisper_model,
            language=language,
            response_format="json",
            temperature=0.0,
            timeout=settings.speech_request_timeout_seconds,
        )
        elapsed = time.perf_counter() - start
        logger.info(
            "Groq response OK in %.2fs filename=%s", elapsed, filename
        )

    except groq.APITimeoutError as exc:
        elapsed = time.perf_counter() - start
        logger.error(
            "Groq request timed out after %.2fs filename=%s: %s",
            elapsed,
            filename,
            exc,
        )
        raise TranscriptionTimeoutError(
            "The transcription service took too long to respond. Please try again."
        ) from exc

    except groq.AuthenticationError as exc:
        logger.error("Groq authentication failed: %s", exc)
        raise MissingAPIKeyError(
            "Speech transcription isn't configured correctly on this server "
            "(the API key was rejected). Check GROQ_API_KEY."
        ) from exc

    except groq.APIStatusError as exc:
        logger.error(
            "Groq returned an error status=%s filename=%s body=%s",
            exc.status_code,
            filename,
            exc.body,
        )
        raise TranscriptionFailedError(
            "The transcription service could not process this audio. "
            "Try re-recording, or use a shorter clip."
        ) from exc

    except groq.APIConnectionError as exc:
        logger.error("Could not reach Groq: %s", exc)
        raise TranscriptionFailedError(
            "Could not reach the transcription service. Check your internet "
            "connection and try again."
        ) from exc

    except groq.GroqError as exc:
        logger.error("Unexpected Groq SDK error filename=%s: %s", filename, exc)
        raise TranscriptionFailedError(
            "Something went wrong while transcribing this audio."
        ) from exc

    transcript = (getattr(transcription, "text", None) or "").strip()

    logger.info("TRANSCRIPT: %s", transcript)

    if not transcript:
        logger.error("Groq returned an empty transcript filename=%s", filename)
        raise TranscriptionFailedError(
            "No speech was detected in that recording. Please try again."
        )

    logger.info("Transcript length=%d filename=%s", len(transcript), filename)
    return transcript
