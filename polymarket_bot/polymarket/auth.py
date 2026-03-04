from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Mapping, Optional

from . import models  # noqa: F401
from ..config import get_settings


class BuilderAuth:
    """
    Utility for signing requests as part of the Polymarket Builder Program.

    The exact signing scheme (e.g., HMAC over method/path/body with a timestamp) should
    be aligned with the official Builder documentation. This implementation uses a
    conventional pattern that can be adapted easily.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.builder_api_key
        self.api_secret = api_secret or settings.builder_api_secret

    def _require_credentials(self) -> None:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Builder API credentials are not configured.")

    def _sign(self, message: str) -> str:
        self._require_credentials()
        secret = self.api_secret or ""
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    def build_headers(
        self,
        method: str,
        path: str,
        body: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Construct headers for a Builder-attributed request.

        Commonly this includes:
        - API key
        - Timestamp
        - Signature over method/path/body/timestamp
        """

        self._require_credentials()
        timestamp = str(int(time.time()))
        payload = body or ""
        message = f"{timestamp}:{method.upper()}:{path}:{payload}"
        signature = self._sign(message)

        headers: Dict[str, str] = {
            "X-Builder-Api-Key": self.api_key or "",
            "X-Builder-Timestamp": timestamp,
            "X-Builder-Signature": signature,
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

