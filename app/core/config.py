# apfrom pydantic import BaseSettingsp/core/config.py

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # OpenAI or OpenAI-compatible API key
    # ...
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")  # Allow empty
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")  # Required for Gemini
    # ...


    # Path where Chroma will persist its DB
    CHROMA_PERSIST_DIR: str = "data/chroma_db"

    # Path to your main PDF
    PDF_PATH: str = "docs/service_doc.pdf"

    class Config:
        env_file = ".env"  # load values from .env file if present


# Create a single settings instance to import everywhere
settings = Settings()
