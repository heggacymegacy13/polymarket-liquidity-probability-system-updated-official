from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

import httpx

from ..config import get_settings
from .auth import BuilderAuth


@dataclass
class RelayerDailyLimits:
    """Daily transaction counters and limits for the relayer."""

    date: date
    tx_count: int
    tx_limit: int


class RelayerClient:
    """
    Client for the Polymarket Builder relayer.

    This integrates gasless execution, proxy/safe wallet management, token approvals,
    and CTF (split/merge/redeem) wrappers where applicable.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.relayer_api_base
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self._auth = BuilderAuth(api_key=settings.relayer_api_key)

    def close(self) -> None:
        self._client.close()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = self._auth.build_headers("POST", path, body=self._serialize(payload))
        resp = self._client.post(path, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _serialize(payload: Dict[str, Any]) -> str:
        import json

        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    # --- Wallet / approvals ---

    def deploy_wallet(self, owner_address: str) -> Dict[str, Any]:
        """Deploy a proxy/safe-style wallet for a given owner address."""

        return self._post("/wallets/deploy", {"owner": owner_address})

    def approve_token(self, wallet_address: str, token_address: str, amount: float) -> Dict[str, Any]:
        """Approve USDC or outcome token for spending via the relayer."""

        return self._post(
            "/tokens/approve",
            {
                "wallet": wallet_address,
                "token": token_address,
                "amount": str(amount),
            },
        )

    # --- CTF wrappers (split/merge/redeem) ---

    def split_ctf(self, wallet_address: str, market_id: str, amount: float) -> Dict[str, Any]:
        """Split CTF into outcome tokens for the specified market."""

        return self._post(
            "/ctf/split",
            {"wallet": wallet_address, "market_id": market_id, "amount": str(amount)},
        )

    def merge_ctf(self, wallet_address: str, market_id: str, amount: float) -> Dict[str, Any]:
        """Merge outcome tokens back into CTF for the specified market."""

        return self._post(
            "/ctf/merge",
            {"wallet": wallet_address, "market_id": market_id, "amount": str(amount)},
        )

    def redeem_ctf(self, wallet_address: str, market_id: str) -> Dict[str, Any]:
        """Redeem CTF after market resolution."""

        return self._post("/ctf/redeem", {"wallet": wallet_address, "market_id": market_id})

    # --- Relayed CLOB orders ---

    def relay_order(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Relay a CLOB order for gasless execution.

        The payload should already be validated and signed as required by the Builder
        Program; this method primarily handles relayer-specific wrapping and limits.
        """

        return self._post("/orders/relay", order_payload)

    def get_daily_limits(self) -> RelayerDailyLimits:
        """
        Retrieve the current day's transaction count and limits.

        This is used by the engine and dashboard to display and enforce daily caps.
        """

        path = "/limits/daily"
        headers = self._auth.build_headers("GET", path)
        resp = self._client.get(path, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return RelayerDailyLimits(
            date=date.fromisoformat(data["date"]),
            tx_count=int(data["tx_count"]),
            tx_limit=int(data["tx_limit"]),
        )

