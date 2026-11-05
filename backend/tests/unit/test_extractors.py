"""Choosing the LLM provider, and the Gemini extractor. No real API is called."""

from types import SimpleNamespace

import pytest
from google.genai import errors

from app.core.config import get_settings
from app.extraction import llm_extractor
from app.extraction.llm_extractor import ExtractionError, GeminiExtractor, OpenAIExtractor, create_extractor

PAGES = [{"page": 1, "text": "Padma Textile Mills Ltd", "source": "pdf_text", "needs_ocr": False}]


class FakeGeminiModels:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.sent = result, error, {}

    def generate_content(self, model, contents, config):
        self.sent.update(model=model, contents=contents, config=config)
        if self.error:
            raise self.error
        return self.result


def use_fake_gemini(monkeypatch, models: FakeGeminiModels) -> None:
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    monkeypatch.setattr(llm_extractor, "create_gemini_client", lambda: SimpleNamespace(models=models))


def test_provider_setting_chooses_the_extractor(monkeypatch):
    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "llm_provider", "openai")
    assert isinstance(create_extractor(), OpenAIExtractor)
    monkeypatch.setattr(get_settings(), "llm_provider", "gemini")
    assert isinstance(create_extractor(), GeminiExtractor)


def test_gemini_without_key_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    with pytest.raises(ExtractionError, match="GEMINI_API_KEY"):
        GeminiExtractor()


def test_gemini_returns_json_text_and_uses_the_shared_prompt(monkeypatch):
    models = FakeGeminiModels(result=SimpleNamespace(text='{"supplier_name": "Padma"}', model_version="gemini-test"))
    use_fake_gemini(monkeypatch, models)

    response = GeminiExtractor(model="gemini-test").extract(PAGES)

    assert response.raw_text == '{"supplier_name": "Padma"}'
    assert response.model_name == "gemini-test"
    assert models.sent["config"].response_mime_type == "application/json"
    assert "untrusted DATA" in models.sent["config"].system_instruction
    assert '<page number="1">' in models.sent["contents"]


def use_deepseek_settings(monkeypatch, **overrides) -> None:
    values = {
        "llm_provider": "deepseek",
        "deepseek_base_url": "https://example.modal.direct/v1",
        "modal_proxy_token_id": "wk-id",
        "modal_proxy_token_secret": "ws-secret",
        "modal_routing_affinity_key": "affinity-1",
        **overrides,
    }
    for name, value in values.items():
        monkeypatch.setattr(get_settings(), name, value)


def test_deepseek_uses_modal_address_key_and_header(monkeypatch):
    use_deepseek_settings(monkeypatch)
    extractor = create_extractor()

    assert isinstance(extractor, OpenAIExtractor) and extractor.provider_name == "DeepSeek"
    assert extractor.model == get_settings().deepseek_model
    assert str(extractor.client.base_url).startswith("https://example.modal.direct/v1")
    assert extractor.client.api_key == "wk-id.ws-secret"
    assert extractor.client.default_headers["Modal-Routing-Affinity-Key"] == "affinity-1"


def test_deepseek_without_tokens_is_a_clear_error(monkeypatch):
    use_deepseek_settings(monkeypatch, modal_proxy_token_secret="")
    with pytest.raises(ExtractionError, match="MODAL_PROXY_TOKEN_SECRET"):
        create_extractor()


def test_deepseek_returns_json_text(monkeypatch):
    use_deepseek_settings(monkeypatch)
    extractor = create_extractor()
    answer = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"supplier_name": "Padma"}'))], model="deepseek-test")
    monkeypatch.setattr(extractor.client.chat.completions, "create", lambda **kwargs: answer)
    assert extractor.extract(PAGES).raw_text == '{"supplier_name": "Padma"}'


@pytest.mark.parametrize("code, message", [(403, "rejected the API key"), (429, "quota"), (503, "overloaded")])
def test_gemini_errors_become_clear_messages(monkeypatch, code, message):
    use_fake_gemini(monkeypatch, FakeGeminiModels(error=errors.APIError(code, {"error": {"message": "x"}})))
    with pytest.raises(ExtractionError, match=message):
        GeminiExtractor().extract(PAGES)
