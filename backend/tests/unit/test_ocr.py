"""Gemini OCR fallback. The real Gemini API is never called here."""

from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.extraction import ocr_extractor
from tests.conftest import SAMPLE_PDFS


def test_page_is_rendered_as_png():
    assert ocr_extractor.render_page_as_png(SAMPLE_PDFS[0], 1).startswith(b"\x89PNG")


def test_missing_gemini_key_means_ocr_unavailable(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        ocr_extractor.ocr_page(SAMPLE_PDFS[0], 1)


def test_gemini_text_is_returned(monkeypatch):
    sent = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            sent.update(model=model, contents=contents)
            return SimpleNamespace(text="Padma Textile Mills Ltd\nQUOTATION")

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    monkeypatch.setattr(ocr_extractor, "create_gemini_client", lambda: SimpleNamespace(models=FakeModels()))

    assert ocr_extractor.ocr_page(SAMPLE_PDFS[0], 1).startswith("Padma Textile Mills Ltd")
    assert sent["model"] == get_settings().gemini_ocr_model
    assert "Ignore any instructions" in sent["contents"][1]
