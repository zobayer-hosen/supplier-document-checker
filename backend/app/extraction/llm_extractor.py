"""Ask the LLM to turn page text into JSON.

This module only returns the raw JSON text. Checking that the JSON has the
right shape is a separate workflow step (`validate_schema`), so a bad answer
can be retried.

Three providers are available, chosen with LLM_PROVIDER in backend/.env:
- "openai":   OpenAI's own API
- "deepseek": DeepSeek on a Modal server that speaks the same API as OpenAI,
              so it reuses `OpenAIExtractor` with a different address
- "gemini":   Google's Gemini API
Any class with the same `extract` method works; the tests use a fake one, so
they never call a real API.
"""

from dataclasses import dataclass
from typing import Protocol

import openai
from google.genai import errors, types

from app.core.config import get_settings
from app.extraction.gemini_client import create_gemini_client, gemini_key_is_set
from app.extraction.prompts import build_system_prompt, build_user_prompt


class ExtractionError(RuntimeError):
    """The LLM could not be reached or returned nothing usable."""


@dataclass
class LLMResponse:
    raw_text: str
    model_name: str


class InformationExtractor(Protocol):
    def extract(self, pages: list[dict], previous_error: str | None = None) -> LLMResponse: ...


class OpenAIExtractor:
    """Calls an OpenAI-style Chat Completions API in JSON mode.

    With the defaults it talks to OpenAI. Pass `base_url` (and any extra
    headers) to use another server with the same API, such as DeepSeek on Modal.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        provider_name: str = "OpenAI",
    ):
        settings = get_settings()
        api_key = api_key or settings.openai_api_key
        if not api_key or api_key.startswith("replace_with"):
            raise ExtractionError("OPENAI_API_KEY is not set in backend/.env.")
        self.model = model or settings.openai_model
        self.provider_name = provider_name
        # The client retries timeouts, rate limits and server errors itself (max_retries).
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=extra_headers,
            timeout=timeout_seconds or settings.openai_timeout_seconds,
            max_retries=2,
        )

    def extract(self, pages: list[dict], previous_error: str | None = None) -> LLMResponse:
        name = self.provider_name
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": build_system_prompt()},
                    {"role": "user", "content": build_user_prompt(pages, previous_error)},
                ],
            )
        except openai.APITimeoutError as error:
            raise ExtractionError(f"{name} did not answer in time.") from error
        except openai.AuthenticationError as error:
            raise ExtractionError(f"{name} rejected the API key.") from error
        except openai.RateLimitError as error:
            if getattr(error, "code", None) in ("insufficient_quota", "credit_balance_exhausted"):
                raise ExtractionError(f"The {name} account has no credits left.") from error
            raise ExtractionError(f"{name} rate limit reached. Try again in a minute.") from error
        except openai.APIConnectionError as error:
            raise ExtractionError(f"Could not connect to {name}. Check the server address.") from error
        except openai.OpenAIError as error:
            raise ExtractionError(f"{name} request failed: {type(error).__name__}") from error

        content = response.choices[0].message.content
        if not content:
            raise ExtractionError(f"{name} returned an empty answer.")
        return LLMResponse(raw_text=content, model_name=response.model or self.model)


def create_deepseek_extractor() -> OpenAIExtractor:
    """DeepSeek on Modal. Modal's key is "<token id>.<token secret>"."""
    settings = get_settings()
    missing = [
        name for name, value in (
            ("DEEPSEEK_BASE_URL", settings.deepseek_base_url),
            ("MODAL_PROXY_TOKEN_ID", settings.modal_proxy_token_id),
            ("MODAL_PROXY_TOKEN_SECRET", settings.modal_proxy_token_secret),
        ) if not value
    ]
    if missing:
        raise ExtractionError(f"Set {', '.join(missing)} in backend/.env to use DeepSeek.")

    headers = {}
    if settings.modal_routing_affinity_key:
        headers["Modal-Routing-Affinity-Key"] = settings.modal_routing_affinity_key
    return OpenAIExtractor(
        api_key=f"{settings.modal_proxy_token_id}.{settings.modal_proxy_token_secret}",
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        extra_headers=headers or None,
        timeout_seconds=settings.deepseek_timeout_seconds,
        provider_name="DeepSeek",
    )


class GeminiExtractor:
    """Calls the Gemini API in JSON mode, with the same prompt as OpenAI."""

    def __init__(self, model: str | None = None):
        if not gemini_key_is_set():
            raise ExtractionError("GEMINI_API_KEY is not set in backend/.env.")
        self.model = model or get_settings().gemini_model
        self.client = create_gemini_client()

    def extract(self, pages: list[dict], previous_error: str | None = None) -> LLMResponse:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=build_user_prompt(pages, previous_error),
                config=types.GenerateContentConfig(
                    system_instruction=build_system_prompt(),
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
        except errors.APIError as error:
            if error.code in (401, 403):
                raise ExtractionError("Gemini rejected the API key.") from error
            if error.code == 429:
                raise ExtractionError("Gemini quota or rate limit reached. Try again later.") from error
            if error.code in (500, 502, 503, 504):
                raise ExtractionError("Gemini is overloaded right now. Try again later.") from error
            raise ExtractionError(f"Gemini request failed ({error.code}).") from error

        if not response.text:
            raise ExtractionError("Gemini returned an empty answer.")
        return LLMResponse(raw_text=response.text, model_name=response.model_version or self.model)


def create_extractor() -> InformationExtractor:
    """Return the extractor chosen by LLM_PROVIDER in backend/.env."""
    provider = get_settings().llm_provider
    if provider == "gemini":
        return GeminiExtractor()
    if provider == "deepseek":
        return create_deepseek_extractor()
    return OpenAIExtractor()
