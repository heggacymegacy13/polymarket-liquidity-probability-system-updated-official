from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import httpx

from .models import Event, Market, OHLCBar, OrderBook, Position, Trade
from ..config import get_settings
from .auth import BuilderAuth


class PolymarketClient:
    """
    Thin wrapper around Polymarket HTTP APIs.

    This class is intentionally conservative and focuses on the key operations
    required by the strategy engine. Exact endpoint paths and parameters should
    be updated to match the official Polymarket Builder documentation.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.polymarket_api_base
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self._auth = BuilderAuth()

    def close(self) -> None:
        self._client.close()

    # --- Markets & events ---

    def fetch_events(self) -> List[Event]:
        """Fetch a list of events from Polymarket."""

        resp = self._client.get("/events")
        resp.raise_for_status()
        data = resp.json()
        return [Event(**item) for item in data]

    def fetch_markets(self) -> List[Market]:
        """Fetch a list of markets."""

        resp = self._client.get("/markets")
        resp.raise_for_status()
        data = resp.json()
        return [Market(**item) for item in data]

    def fetch_market(self, market_id: str) -> Market:
        """Fetch a single market by id."""

        resp = self._client.get(f"/markets/{market_id}")
        resp.raise_for_status()
        return Market(**resp.json())

    def fetch_order_book(self, market_id: str) -> OrderBook:
        """Fetch an order book snapshot for the given market."""

        resp = self._client.get(f"/markets/{market_id}/orderbook")
        resp.raise_for_status()
        data = resp.json()
        return OrderBook(**data)

    # --- User state ---

    def fetch_positions(self, wallet_address: str) -> List[Position]:
        """
        Fetch positions for the given wallet.

        The exact shape depends on Polymarket's API; this method assumes a list of
        position-like objects that can be parsed into `Position`.
        """

        resp = self._client.get(f"/wallets/{wallet_address}/positions")
        resp.raise_for_status()
        return [Position(**item) for item in resp.json()]

    # --- Trades / OHLC ---

    def fetch_recent_trades(self, market_id: str, limit: int = 100) -> List[Trade]:
        """Fetch recent trades for a given market."""

        resp = self._client.get(f"/markets/{market_id}/trades", params={"limit": limit})
        resp.raise_for_status()
        return [Trade(**item) for item in resp.json()]

    def fetch_ohlc(
        self,
        market_id: str,
        outcome_id: str,
        start: datetime,
        end: datetime,
        interval: str = "1m",
    ) -> List[OHLCBar]:
        """
        Fetch or derive OHLC-style data for a market/outcome.

        Implementations may call a dedicated OHLC endpoint or derive the bars from
        raw trades.
        """

        resp = self._client.get(
            f"/markets/{market_id}/ohlc",
            params={
                "outcome_id": outcome_id,
                "start": int(start.timestamp()),
                "end": int(end.timestamp()),
                "interval": interval,
            },
        )
        resp.raise_for_status()
        return [OHLCBar(**item) for item in resp.json()]

