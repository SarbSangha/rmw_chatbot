from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")

    CHROMA_PERSIST_DIR: str = Field(default="data/chroma_db", env="CHROMA_PERSIST_DIR")
    PDF_PATH: str = Field(default="docs/RMW.docx", env="PDF_PATH")

    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Comma-separated list. Example:
    # http://localhost:5173,http://127.0.0.1:5173,https://yourdomain.com
    ALLOWED_ORIGINS: str = Field(default="*", env="ALLOWED_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def allowed_origins_list(self) -> list[str]:
        raw = (self.ALLOWED_ORIGINS or "").strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
