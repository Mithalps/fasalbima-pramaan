class ClaimNotFoundError(Exception):
    """Raised when a claim_id does not exist. Routers translate this to a 404."""

    def __init__(self, claim_id: str):
        self.claim_id = claim_id
        super().__init__(f"Claim '{claim_id}' was not found")


class SpeechServiceError(Exception):
    """
    Base class for every speech-transcription failure. Each subclass carries
    the HTTP status code the router should respond with, so the router never
    has to guess which status fits which failure.
    """

    status_code = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class MissingAPIKeyError(SpeechServiceError):
    """GROQ_API_KEY is not configured on the server — this is a server misconfiguration, not the caller's fault."""

    status_code = 500


class EmptyAudioError(SpeechServiceError):
    """The uploaded audio file had zero bytes."""

    status_code = 400


class UnsupportedAudioTypeError(SpeechServiceError):
    """The uploaded file's content type isn't one Groq Whisper accepts."""

    status_code = 400


class AudioTooLargeError(SpeechServiceError):
    """The uploaded file exceeds the configured size limit."""

    status_code = 413


class TranscriptionTimeoutError(SpeechServiceError):
    """Groq did not respond within the configured timeout."""

    status_code = 504


class TranscriptionFailedError(SpeechServiceError):
    """Groq responded, but with an error, or with a response we couldn't use."""

    status_code = 502


class ClassifierServiceError(Exception):
    """Base class for image-classification failures. Mirrors SpeechServiceError's shape."""

    status_code = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ClassifierNotReadyError(ClassifierServiceError):
    """The model failed to load at startup (missing/corrupt checkpoint)."""

    status_code = 503


class EmptyImageError(ClassifierServiceError):
    """The uploaded image file had zero bytes."""

    status_code = 400


class ImageTooLargeError(ClassifierServiceError):
    """The uploaded image exceeds the configured size limit."""

    status_code = 413


class UnsupportedImageTypeError(ClassifierServiceError):
    """The uploaded file's content type isn't an image type we accept."""

    status_code = 400


class InvalidImageError(ClassifierServiceError):
    """The uploaded bytes could not be decoded as an image."""

    status_code = 400


