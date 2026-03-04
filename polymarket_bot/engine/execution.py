from __future__ import annotations

import time
from datetime import datetime
from typing import Iterable, List, Mapping

from ..logging_config import get_logger
from ..polymarket.client import PolymarketClient
from ..polymarket.clob import CLOBClient
from ..polymarket.models import Market, Order, OrderBook, Position
from ..polymarket.relayer import RelayerClient
from ..strategies.base import BaseStrategy, StrategyConfig
from .metrics import MetricsCollector
from .portfolio import Key, Portfolio
from .risk import RiskManager, StrategyLimits

logger = get_logger(__name__)


class ExecutionEngine:
    """
    Orchestrates strategies, market data, risk checks, and order submission.
    """

    def __init__(
        self,
        strategies: Iterable[BaseStrategy],
        client: PolymarketClient | None = None,
        clob: CLOBClient | None = None,
        relayer: RelayerClient | None = None,
        metrics: MetricsCollector | None = None,
        portfolio: Portfolio | None = None,
        risk_manager: RiskManager | None = None,
        dry_run: bool = False,
    ) -> None:
        self.strategies = list(strategies)
        self.client = client or PolymarketClient()
        self.clob = clob or CLOBClient(self.client)
        self.relayer = relayer or RelayerClient()
        self.metrics = metrics or MetricsCollector()
        self.portfolio = portfolio or Portfolio()
        self.risk_manager = risk_manager or RiskManager()
        self.dry_run = dry_run

    def _fetch_markets(self, market_ids: Iterable[str]) -> Mapping[str, Market]:
        all_markets = self.client.fetch_markets()
        wanted = set(market_ids)
        return {m.id: m for m in all_markets if m.id in wanted}

    def _fetch_order_books(self, markets: Mapping[str, Market]) -> Mapping[str, OrderBook]:
        books: dict[str, OrderBook] = {}
        for market_id in markets:
            books[market_id] = self.client.fetch_order_book(market_id)
        return books

    def _fetch_positions(self) -> List[Position]:
        # In a full implementation we would read the configured wallet address.
        from ..config import get_settings

        wallet = get_settings().wallet_address
        if not wallet:
            return []
        return self.client.fetch_positions(wallet)

    def _strategy_limits(self, config: StrategyConfig) -> StrategyLimits:
        return StrategyLimits(
            name=config.name,
            max_order_size=config.max_order_size,
            max_position_per_market=config.max_position_per_market,
        )

    def run_once(self) -> None:
        """
        Single iteration over all strategies:
        - Fetch market data & positions.
        - Invoke strategies.
        - Apply risk checks.
        - Submit or log orders.
        """

        now = datetime.utcnow()
        all_market_ids = {
            m_id for strategy in self.strategies for m_id in strategy.subscribed_markets
        }
        markets = self._fetch_markets(all_market_ids)
        books = self._fetch_order_books(markets)
        positions = self._fetch_positions()
        self.portfolio.update_from_positions(positions)

        positions_by_market: dict[str, Position] = {
            p.market_id: p for p in positions
        }

        for strategy in self.strategies:
            for market_id in strategy.subscribed_markets:
                market = markets.get(market_id)
                book = books.get(market_id)
                if not market or not book:
                    continue
                strategy.on_market_data(
                    market=market,
                    order_book=book,
                    positions=positions_by_market,
                    now=now,
                )

            proposed_orders: List[Order] = strategy.generate_orders()
            limits = self._strategy_limits(strategy.config)

            for order in proposed_orders:
                key: Key = (order.market_id, order.outcome_id)
                current_prices = {key: order.price}
                market_notional = self.portfolio.total_notional(current_prices)
                total_notional = market_notional  # simplified global exposure calc

                if not self.risk_manager.check_order(
                    limits,
                    order,
                    current_market_notional=market_notional,
                    current_total_notional=total_notional,
                ):
                    continue

                notional = order.price * abs(order.size)
                self.metrics.record_order_submission(strategy.name, order.market_id, notional)

                if self.dry_run:
                    logger.info(
                        "[DRY RUN] Would submit order: strategy=%s market=%s side=%s price=%.4f size=%.4f",  # noqa: E501
                        strategy.name,
                        order.market_id,
                        order.side.value,
                        order.price,
                        order.size,
                    )
                    continue

                submitted = self.clob.submit_limit_order(
                    # Convert Order to OrderRequest in a full implementation; here we
                    # call lower-level CLOB inline for simplicity.
                    # type: ignore[arg-type]
                    order  # noqa: ARG001
                )
                logger.info(
                    "Submitted order: id=%s market=%s side=%s price=%.4f size=%.4f",
                    submitted.id,
                    submitted.market_id,
                    submitted.side.value,
                    submitted.price,
                    submitted.size,
                )

    def run_forever(self, interval_seconds: float = 5.0) -> None:
        """Main loop."""

        logger.info("Starting execution engine (interval=%ss dry_run=%s)", interval_seconds, self.dry_run)  # noqa: E501
        try:
            while True:
                self.run_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Execution engine stopped by user.")

