from __future__ import annotations

from datetime import datetime

from polymarket_bot.polymarket.models import Market, OrderBook, OrderBookLevel, Position
from polymarket_bot.strategies.base import StrategyConfig
from polymarket_bot.strategies.mm_spread_tightener import MMConfig, SpreadTightenerStrategy


def test_mm_spread_tightener_generates_two_sided_quotes() -> None:
    cfg = MMConfig(
        name="test-mm",
        markets=["m1"],
        max_position_per_market=500.0,
        max_order_size=100.0,
        quote_size=10.0,
        inventory_skew_sensitivity=0.5,
        per_market_params={},
    )
    strat = SpreadTightenerStrategy(cfg)
    market = Market(
        id="m1",
        event_id="e1",
        question="Test?",
        outcomes=[],
    )
    book = OrderBook(
        market_id="m1",
        bids=[OrderBookLevel(price=0.45, size=100)],
        asks=[OrderBookLevel(price=0.55, size=100)],
    )
    positions = {"m1": Position(market_id="m1", outcome_id="m1", size=0.0, avg_entry_price=None, unrealized_pnl=None)}  # noqa: E501
    strat.on_market_data(market, book, positions, datetime.utcnow())
    orders = strat.generate_orders()
    assert len(orders) == 2
    sides = {o.side for o in orders}
    assert len(sides) == 2

