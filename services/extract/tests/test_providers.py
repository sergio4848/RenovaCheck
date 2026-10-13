"""Cloud OCR adapters and the optional LLM helper, without network access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from PIL import Image

from renova_extract.core.config import Settings
from renova_extract.documents.models import Page, TextSource, Word
from renova_extract.fields import llm
from renova_extract.fields.dictionary import FieldDictionary
from renova_extract.fields.extractors import FieldExtractor
from renova_extract.fields.layout import layout
from renova_extract.ocr.azure import AzureDocumentIntelligence
from renova_extract.ocr.base import OcrUnavailableError
from renova_extract.ocr.google import GoogleDocumentAI
from tests.conftest import make_settings

OCR_FIXTURES = Path(__file__).parent / "fixtures" / "ocr"
DICTIONARY = FieldDictionary.from_yaml(Settings().rules_dir / "fields.yaml")
IMAGE = Image.new("L", (1240, 1754), 255)
ENDPOINT = "https://polandcentral.api.cognitive.microsoft.com"


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((OCR_FIXTURES / name).read_text())


def _page_of(words: list[Word]) -> Page:
    return Page(1, 595.0, 842.0, IMAGE, words, TextSource.OCR)


def _invoice_fields(words: list[Word]) -> dict[str, Any]:
    return {f.name: f.value for f in FieldExtractor(DICTIONARY).extract([_page_of(words)], "faktura")}


# ---------------------------------------------------------------------------- Azure
def test_azure_polls_the_operation_and_parses_words() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(202, headers={"Operation-Location": f"{ENDPOINT}/documentintelligence/op/1"})
        if len(calls) == 2:
            return httpx.Response(200, json={"status": "running"})
        return httpx.Response(200, json=_fixture("azure_read_result.json"))

    adapter = AzureDocumentIntelligence(
        ENDPOINT, "key-123", client=httpx.Client(transport=httpx.MockTransport(handler)), poll_interval_seconds=0
    )
    words = adapter.recognize(IMAGE)

    assert calls[0].headers["Ocp-Apim-Subscription-Key"] == "key-123"
    assert calls[0].headers["Content-Type"] == "image/png"
    assert "prebuilt-read:analyze" in str(calls[0].url)
    assert [w.text for w in words][:4] == ["Faktura", "VAT", "nr", "FV/145/05/2026"]
    assert words[0].x0 == pytest.approx(100 / 1240) and words[0].y1 == pytest.approx(125 / 1754)
    assert _invoice_fields(words) == {"document_number": "FV/145/05/2026", "amount_gross": "49522.27"}


def test_azure_never_sends_the_key_to_another_host() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        return httpx.Response(202, headers={"Operation-Location": "https://attacker.example/op"})

    adapter = AzureDocumentIntelligence(
        ENDPOINT, "key-123", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(OcrUnavailableError):
        adapter.recognize(IMAGE)
    assert seen == ["polandcentral.api.cognitive.microsoft.com"]


def test_azure_errors_become_ocr_unavailable() -> None:
    adapter = AzureDocumentIntelligence(
        ENDPOINT, "key", client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401)))
    )
    with pytest.raises(OcrUnavailableError):
        adapter.recognize(IMAGE)


# ---------------------------------------------------------------------------- Google
def test_google_parses_tokens_from_text_anchors() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_fixture("google_process_response.json"))

    adapter = GoogleDocumentAI(
        "proj", "eu", "proc", "token-1", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    words = adapter.recognize(IMAGE)

    assert requests[0].url.host == "eu-documentai.googleapis.com"
    assert requests[0].headers["Authorization"] == "Bearer token-1"
    assert json.loads(requests[0].content)["rawDocument"]["mimeType"] == "image/png"
    assert [w.text for w in words] == [
        "Faktura",
        "VAT",
        "nr",
        "FV/145/05/2026",
        "Razem",
        "brutto:",
        "49",
        "522,27",
        "zł",
    ]
    assert _invoice_fields(words) == {"document_number": "FV/145/05/2026", "amount_gross": "49522.27"}


def test_provider_settings_are_required_when_selected() -> None:
    with pytest.raises(ValueError, match="RENOVA_AZURE_DI_KEY"):
        make_settings(ocr_provider="azure", azure_di_key="")
    with pytest.raises(ValueError, match="RENOVA_ANTHROPIC_API_KEY"):
        make_settings(llm_provider="anthropic")
    with pytest.raises(ValueError, match="RENOVA_LLM_PROVIDER"):
        make_settings(environment="production", internal_token="x" * 32, s3_secret_key="s" * 20, llm_provider="fake")


# ---------------------------------------------------------------------------- LLM helper
def _text_page() -> Page:
    words = [
        Word("Numer", 0.1, 0.3, 0.15, 0.31),
        Word("seryjny:", 0.16, 0.3, 0.22, 0.31),
        Word("SN38054676", 0.23, 0.3, 0.32, 0.31),
    ]
    return _page_of(words)


def _accept(proposals: list[llm.Proposal]) -> dict[str, Any]:
    pages = layout([_text_page()])
    specs = [DICTIONARY.get("serial_number"), DICTIONARY.get("amount_net")]
    return {f.name: f for f in llm.accept(proposals, specs, pages)}


def test_llm_proposals_must_be_printed_on_the_page() -> None:
    accepted = _accept(
        [
            llm.Proposal(name="serial_number", text="SN38054676", page=1),
            llm.Proposal(name="amount_net", text="45 700,20 zł", page=1),  # not printed: invented
        ]
    )
    assert set(accepted) == {"serial_number"}
    field = accepted["serial_number"]
    assert field.method == "llm" and field.confidence <= 0.5
    assert field.bbox.x0 == pytest.approx(0.23)


def test_llm_proposals_for_unrequested_fields_or_pages_are_dropped() -> None:
    assert _accept([llm.Proposal(name="investor_name", text="SN38054676", page=1)]) == {}
    assert _accept([llm.Proposal(name="serial_number", text="SN38054676", page=2)]) == {}


def test_anthropic_helper_sends_temperature_zero_and_validates_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def fake_post(url: str, json: dict[str, Any], headers: dict[str, str], timeout: float) -> httpx.Response:
        sent.update(url=url, body=json, headers=headers)
        answer = '{"fields": [{"name": "serial_number", "text": "SN38054676", "page": 1}]}'
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": answer}]}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    helper = llm.AnthropicFieldHelper("sk-test", "claude-sonnet-5-5", "https://api.anthropic.com", 5.0)
    proposals = helper.propose([DICTIONARY.get("serial_number")], [(1, "Numer seryjny: SN38054676")])

    assert sent["url"] == "https://api.anthropic.com/v1/messages"
    assert sent["body"]["temperature"] == 0
    assert sent["headers"]["x-api-key"] == "sk-test"
    assert proposals == [llm.Proposal(name="serial_number", text="SN38054676", page=1)]


@pytest.mark.parametrize(
    "answer",
    ["not json", '{"fields": [{"name": "x", "text": "", "page": 1}]}', '{"fields": "all"}', '{"other": 1}'],
)
def test_anthropic_helper_ignores_malformed_answers(monkeypatch: pytest.MonkeyPatch, answer: str) -> None:
    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": answer}]}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    helper = llm.AnthropicFieldHelper("sk-test", "m", "https://api.anthropic.com", 5.0)
    assert helper.propose([DICTIONARY.get("serial_number")], [(1, "x")]) == []
