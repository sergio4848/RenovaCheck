from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_defaults_are_safe_offline_modes() -> None:
    settings = make_settings()
    assert settings.ocr_provider == "text_layer"
    assert settings.llm_provider == "off"


def test_production_rejects_development_secrets() -> None:
    with pytest.raises(ValidationError, match="RENOVA_INTERNAL_TOKEN"):
        make_settings(environment="production")


def test_secrets_are_not_rendered() -> None:
    settings = make_settings(internal_token="super-secret-value")
    assert "super-secret-value" not in repr(settings)


def test_unknown_ocr_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(ocr_provider="magic")
