from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MarketStatus(str, Enum):
    """Lifecycle status of a Polymarket market."""

    OPEN = "open"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class OrderSide(str, Enum):
    """Order side for CLOB orders."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type for CLOB orders."""

    LIMIT = "limit"


class Event(BaseModel):
    """
    Representation of a Polymarket event.

    In Polymarket terminology, an event groups related markets (e.g., a question about
    a real-world outcome). This model mirrors the "Events" section of the official
    Markets & Events documentation.
    """

    id: str = Field(..., description="Unique identifier of the event.")
    title: str = Field(..., description="Human-readable title of the event.")
    description: Optional[str] = Field(
        None, description="Long-form description of the event and its resolution criteria."
    )
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the event was created on Polymarket."
    )
    categories: List[str] = Field(
        default_factory=list, description="Categories/tags associated with the event."
    )


class Outcome(BaseModel):
    """
    Outcome within a market.

    Each market has one or more outcomes (e.g., YES/NO, multiple-choice answers).
    """

    id: str = Field(..., description="Unique identifier of the outcome token/contract.")
    name: str = Field(..., description="Display name of the outcome.")
    symbol: Optional[str] = Field(None, description="Symbol/ticker representing the outcome.")


class Market(BaseModel):
    """
    Polymarket market.

    A market represents a tradable view on an event, typically with multiple outcomes.
    """

    id: str = Field(..., description="Unique identifier of the market.")
    event_id: str = Field(..., description="Identifier of the parent event.")
    question: str = Field(..., description="Human-readable market question.")
    outcomes: List[Outcome] = Field(
        default_factory=list, description="List of outcomes available in this market."
    )
    status: MarketStatus = Field(
        MarketStatus.OPEN, description="Lifecycle status of the market (open/resolved/cancelled)."
    )
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the market was created."
    )
    close_time: Optional[datetime] = Field(
        None, description="Scheduled closing time for trading on this market, if available."
    )


class OrderBookLevel(BaseModel):
    """One level in an order book."""

    price: float = Field(..., description="Price of the level in quote currency.")
    size: float = Field(..., description="Total size available at this price.")


class OrderBook(BaseModel):
    """
    Lightweight order book snapshot for a market.

    This can be derived from Polymarket order book endpoints and used by strategies
    to infer mid-price, spread, and available depth.
    """

    market_id: str = Field(..., description="Identifier of the market this book belongs to.")
    bids: List[OrderBookLevel] = Field(default_factory=list, description="Bid side levels.")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="Ask side levels.")
    timestamp: Optional[datetime] = Field(
        None, description="Time when the snapshot was taken (exchange or local)."
    )


class Order(BaseModel):
    """
    Representation of a CLOB order.

    This mirrors the structure of orders submitted through Polymarket's CLOB as part
    of the Builder Program. Exact fields should be aligned with the official API.
    """

    id: Optional[str] = Field(
        None,
        description="Exchange-assigned unique identifier of the order (may be None before submission).",
    )
    market_id: str = Field(..., description="Identifier of the market this order targets.")
    outcome_id: str = Field(..., description="Identifier of the outcome token for this order.")
    side: OrderSide = Field(..., description="BUY or SELL.")
    type: OrderType = Field(OrderType.LIMIT, description="Order type (currently only LIMIT).")
    price: float = Field(..., description="Limit price in quote currency.")
    size: float = Field(..., description="Order size in base units (e.g., outcome tokens).")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the order was created."
    )
    status: Optional[str] = Field(
        None,
        description="Exchange-reported status (e.g., open, partially_filled, filled, cancelled).",
    )


class Trade(BaseModel):
    """
    Executed trade in a Polymarket market.

    Trades can be used to derive OHLC-like data and realized volatility.
    """

    id: str = Field(..., description="Unique identifier of the trade.")
    market_id: str = Field(..., description="Identifier of the market traded.")
    outcome_id: str = Field(..., description="Outcome involved in the trade.")
    price: float = Field(..., description="Execution price.")
    size: float = Field(..., description="Executed size.")
    side: OrderSide = Field(..., description="Aggressor side (BUY or SELL).")
    timestamp: datetime = Field(..., description="Execution time.")


class Position(BaseModel):
    """
    Current position in a specific outcome token.

    This typically aligns with wallet balances of outcome tokens, plus metadata.
    """

    market_id: str = Field(..., description="Market associated with this position.")
    outcome_id: str = Field(..., description="Outcome token identifier.")
    size: float = Field(..., description="Net position size (positive = long, negative = short).")
    avg_entry_price: Optional[float] = Field(
        None, description="Average entry price for the current position, if tracked."
    )
    unrealized_pnl: Optional[float] = Field(
        None, description="Unrealized PnL based on latest mark price, if available."
    )


class PortfolioSnapshot(BaseModel):
    """Snapshot of positions across all markets at a point in time."""

    timestamp: datetime
    positions: List[Position]


class OHLCBar(BaseModel):
    """
    Derived OHLC-style data for a given market/outcome over a time bucket.
    """

    market_id: str
    outcome_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    start_time: datetime
    end_time: datetime


class MetricsSnapshot(BaseModel):
    """
    In-memory snapshot of engine metrics for display in the dashboard.
    """

    date: datetime
    relayer_tx_count: int
    relayer_tx_limit: int
    volume_by_market: Dict[str, float] = Field(default_factory=dict)
    markets_traded: int = 0
    strategies_activity: Dict[str, int] = Field(
        default_factory=dict, description="Number of orders submitted per strategy."
    )

