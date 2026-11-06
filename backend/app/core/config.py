"""Application settings, loaded from environment variables or `backend/.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 60
    database_url: str = ""

    max_file_size_mb: int = 20
    max_pdf_pages: int = 100
    max_extraction_retries: int = 2
    upload_directory: str = "uploads"
    # Comma-separated frontend addresses allowed to call the API (local dev and the Vercel deployment)
    cors_origins: str = "http://localhost:3000,https://supplier-document-checker.vercel.app"

    # Which LLM extracts information: "openai", "gemini" or "deepseek"
    llm_provider: Literal["openai", "gemini", "deepseek"] = "gemini"

    # DeepSeek on a Modal server (OpenAI-compatible API)
    deepseek_base_url: str = ""
    deepseek_model: str = "deepseek-ai/DeepSeek-V4.1-Flash"
    deepseek_timeout_seconds: float = 180  # a sleeping Modal server can take a while to start
    modal_proxy_token_id: str = ""
    modal_proxy_token_secret: str = ""
    modal_routing_affinity_key: str = ""

    # Gemini: extraction (when llm_provider is "gemini") and OCR of scanned pages
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_ocr_model: str = "gemini-3.6-flash"
    gemini_timeout_seconds: float = 60

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        """Upload folder as an absolute path (relative paths start at `backend/`)."""
        path = Path(self.upload_directory)
        return path if path.is_absolute() else BACKEND_DIRECTORY / path

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return one shared Settings object (read from the environment only once)."""
    return Settings()
