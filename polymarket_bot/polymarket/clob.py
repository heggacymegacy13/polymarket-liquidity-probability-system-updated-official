from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import PolymarketClient
from .models import Order, OrderBook, OrderSide
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OrderRequest:
    """High-level order intent produced by strategies."""

    market_id: str
    outcome_id: str
    side: OrderSide
    price: float
    size: float


def mid_price(order_book: OrderBook) -> Optional[float]:
    """Compute mid-price from the best bid/ask."""

    best_bid = order_book.bids[0].price if order_book.bids else None
    best_ask = order_book.asks[0].price if order_book.asks else None
    if best_bid is None or best_ask is None:
        return None
    return (best_bid + best_ask) / 2.0


def spread_bps(order_book: OrderBook) -> Optional[float]:
    """Compute current spread in basis points."""

    best_bid = order_book.bids[0].price if order_book.bids else None
    best_ask = order_book.asks[0].price if order_book.asks else None
    if best_bid is None or best_ask is None or best_bid <= 0:
        return None
    return (best_ask - best_bid) / best_bid * 10_000.0


class CLOBClient:
    """
    Helper for constructing and submitting CLOB orders.

    This class delegates actual HTTP communication to `PolymarketClient`, but
    centralizes order construction, precision handling, and logging.
    """

    def __init__(self, client: Optional[PolymarketClient] = None) -> None:
        self.client = client or PolymarketClient()

    # --- Precision helpers ---

    @staticmethod
    def normalize_price(price: float, tick_size: float = 0.0001) -> float:
        """Round price to the nearest tick size."""

        ticks = round(price / tick_size)
        return ticks * tick_size

    @staticmethod
    def normalize_size(size: float, step: float = 0.0001) -> float:
        """Round size to the nearest lot size."""

        lots = round(size / step)
        return lots * step

    # --- Order submission ---

    def build_order_payload(self, req: OrderRequest) -> Dict[str, Any]:
        """
        Convert an `OrderRequest` into a payload suitable for the CLOB API.

        This method should be updated to match the exact schema expected by
        Polymarket's Builder Program.
        """

        normalized_price = self.normalize_price(req.price)
        normalized_size = self.normalize_size(req.size)
        payload: Dict[str, Any] = {
            "market_id": req.market_id,
            "outcome_id": req.outcome_id,
            "side": req.side.value,
            "type": "limit",
            "price": str(normalized_price),
            "size": str(normalized_size),
        }
        return payload

    def submit_limit_order(self, req: OrderRequest) -> Order:
        """Submit a limit order and return the resulting Order model."""

        payload = self.build_order_payload(req)
        logger.info(
            "Submitting order: market=%s outcome=%s side=%s price=%s size=%s",
            req.market_id,
            req.outcome_id,
            req.side.value,
            payload["price"],
            payload["size"],
        )
        resp = self.client._client.post("/clob/orders", json=payload)  # noqa: SLF001
        resp.raise_for_status()
        return Order(**resp.json())

    def cancel_order(self, order_id: str) -> None:
        """Cancel an existing order."""

        logger.info("Cancelling order %s", order_id)
        resp = self.client._client.delete(f"/clob/orders/{order_id}")  # noqa: SLF001
        resp.raise_for_status()

