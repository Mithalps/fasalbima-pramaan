from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Centralized application configuration.

    Every later module (ASR, weather, classifier, PDF generation) reads
    its configuration from here instead of hardcoding values, so the
    only place you ever need to put a real API key or path is the
    project's .env file.
    """

    # General
    app_name: str = "FasalBima Pramaan API"
    environment: str = "development"

    # CORS — the origin(s) allowed to call this API from the browser
    frontend_origin: str = "http://localhost:5173"

    # Database
    database_url: str = "sqlite:///./data/fasalbima.db"

    # Reserved for a later module (Module 8: Open-Meteo weather validation).
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

    # Image classification (Feature 5: MobileNetV2 damage severity classifier)
    # Paths are relative to the backend/ working directory, matching the
    # convention already used by database_url above.
    classifier_checkpoint_path: str = "../ml/outputs/checkpoints/best_model.pth"
    classifier_class_names_path: str = "../ml/outputs/checkpoints/class_names.json"
    classifier_max_image_size_mb: int = 10


    # Speech-to-text (Feature 2: Voice Assistance via Groq Whisper)
    groq_api_key: str = ""
    groq_whisper_model: str = "whisper-large-v3"
    # Kannada is this project's stated differentiator; callers can still
    # override the language per-request (see routers/speech.py).
    speech_default_language: str = "kn"
    speech_max_audio_size_mb: int = 15
    speech_request_timeout_seconds: float = 25.0
    # Weather validation (Module 10: Open-Meteo historical weather check)
    weather_request_timeout_seconds: float = 10.0




    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Evidence upload
    upload_dir: str = "./uploads"
    upload_url_prefix: str = "/uploads"
    max_evidence_file_size_mb: int = 10
    max_evidence_images_per_claim: int = 5

# Single shared settings instance imported throughout the app
settings = Settings()
