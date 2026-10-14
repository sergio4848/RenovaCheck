"""Request dependencies: service-to-service authentication."""

from __future__ import annotations

import hmac

from fastapi import Request

from renova_extract.core.config import Settings
from renova_extract.core.errors import AuthenticationRequiredError


def require_internal_token(request: Request) -> None:
    settings: Settings = request.app.state.settings
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    expected = settings.internal_token.get_secret_value()
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.encode(), expected.encode()):
        raise AuthenticationRequiredError()
