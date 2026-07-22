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
# ------------------------------------------------------------------
# Evidence upload compatibility aliases
# ------------------------------------------------------------------

class FileTooLargeError(ImageTooLargeError):
    """Backward-compatible alias for evidence uploads."""
    pass


class UnsupportedFileTypeError(UnsupportedImageTypeError):
    """Backward-compatible alias for evidence uploads."""
    pass


class EvidenceNotFoundError(Exception):
    """Raised when an evidence image cannot be found."""

    def __init__(self, evidence_id: str):
        self.evidence_id = evidence_id
        super().__init__(f"Evidence '{evidence_id}' was not found")


class EvidenceLimitExceededError(Exception):
    """Raised when more than the maximum number of evidence images are uploaded."""

    def __init__(self, limit: int = 5):
        self.limit = limit
        super().__init__(f"A claim can contain at most {limit} evidence images.")

class WeatherValidationError(Exception):
    """Base class for weather-validation failures."""

    status_code = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidDateError(WeatherValidationError):
    """The damage_date is malformed or in the future."""

    status_code = 400

    def __init__(self, date_value: str):
        super().__init__(f"'{date_value}' is not a valid past date.")


class LocationNotFoundError(WeatherValidationError):
    """The district/village could not be geocoded."""

    status_code = 404

    def __init__(self, district: str):
        super().__init__(f"Could not resolve location for district '{district}'.")


class WeatherDataUnavailableError(WeatherValidationError):
    """Open-Meteo has no historical data for the requested date/location."""

    status_code = 502

    def __init__(self, date_value: str):
        super().__init__(f"No weather data available for {date_value}.")


class WeatherServiceUnavailableError(WeatherValidationError):
    """Open-Meteo itself could not be reached."""

    status_code = 503

class WeatherValidationError(Exception):
    """Base class for weather-validation failures."""

    status_code = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidDateError(WeatherValidationError):
    """The damage_date is malformed or in the future."""

    status_code = 400

    def __init__(self, date_value: str):
        super().__init__(f"'{date_value}' is not a valid past date.")


class LocationNotFoundError(WeatherValidationError):
    """The district/village could not be geocoded."""

    status_code = 404

    def __init__(self, district: str):
        super().__init__(f"Could not resolve location for district '{district}'.")


class WeatherDataUnavailableError(WeatherValidationError):
    """Open-Meteo has no historical data for the requested date/location."""

    status_code = 502

    def __init__(self, date_value: str):
        super().__init__(f"No weather data available for {date_value}.")


class WeatherServiceUnavailableError(WeatherValidationError):
    """Open-Meteo itself could not be reached."""

    status_code = 503    