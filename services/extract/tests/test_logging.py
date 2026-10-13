from __future__ import annotations

from renova_extract.core.logging import REDACTED, redact_sensitive


def test_polish_identifiers_and_addresses_are_redacted() -> None:
    event = {
        "event": "x",
        "nip": "0012345678",
        "payload": {"address": "ul. Sosnowa 12", "inwestor_name": "Jan", "page": 2},
        "s3_access_key": "abc",
    }
    out = redact_sensitive(None, "info", dict(event))
    assert out["nip"] == REDACTED
    assert out["payload"]["address"] == REDACTED
    assert out["payload"]["inwestor_name"] == REDACTED
    assert out["payload"]["page"] == 2
    assert out["s3_access_key"] == REDACTED
