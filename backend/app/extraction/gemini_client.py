"""One place to create the Gemini client, shared by OCR and extraction."""

from google import genai
from google.genai import types

from app.core.config import get_settings

# Retry when Google is busy (429 rate limit, 500/503 overloaded), waiting longer each time.
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]


def gemini_key_is_set() -> bool:
    key = get_settings().gemini_api_key
    return bool(key) and not key.startswith("replace_with")


def create_gemini_client() -> genai.Client:
    """Return a Gemini client. Keep a reference to it while the request runs."""
    settings = get_settings()
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=int(settings.gemini_timeout_seconds * 1000),
            retry_options=types.HttpRetryOptions(
                attempts=4, initial_delay=2, max_delay=30, http_status_codes=RETRY_STATUS_CODES,
            ),
        ),
    )
