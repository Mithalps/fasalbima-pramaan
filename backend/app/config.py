from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Evidence upload (Feature 2)
    # Path is relative to the backend/ working directory, same convention as database_url.
    upload_dir: str = "./uploads"
    upload_url_prefix: str = "/uploads"
    max_evidence_file_size_mb: int = 10
    max_evidence_images_per_claim: int = 5

    # Reserved for later modules (Module 6: Whisper, Module 8: Open-Meteo).
    # Declared now so .env.example documents them from the start.
    whisper_model_size: str = "small"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Single shared settings instance imported throughout the app
settings = Settings()
