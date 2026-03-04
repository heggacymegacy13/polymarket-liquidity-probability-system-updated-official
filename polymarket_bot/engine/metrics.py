from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict

from ..logging_config import get_logger
from ..polymarket.models import MetricsSnapshot
from ..storage.db import Metric, session_scope

logger = get_logger(__name__)


@dataclass
class MetricsCollector:
    """
    In-memory and persisted metrics for engine activity.

    This is the central place where the engine reports:
    - Daily relayer transaction counts.
    - Volume routed per day/week.
    - Number of markets traded.
    - Per-strategy activity metrics.
    """

    relayer_tx_count: int = 0
    relayer_tx_limit: int = 3_000
    volume_by_market: Dict[str, float] = field(default_factory=dict)
    strategies_activity: Dict[str, int] = field(default_factory=dict)
    markets_traded: Dict[str, bool] = field(default_factory=dict)

    def record_order_submission(self, strategy_name: str, market_id: str, notional: float) -> None:
        """Record an order submission for metrics purposes."""

        logger.debug(
            "Recording order submission: strategy=%s market=%s notional=%.4f",
            strategy_name,
            market_id,
            notional,
        )
        self.volume_by_market[market_id] = self.volume_by_market.get(market_id, 0.0) + notional
        self.strategies_activity[strategy_name] = self.strategies_activity.get(strategy_name, 0) + 1
        self.markets_traded[market_id] = True

    def record_relayer_tx(self) -> None:
        """Increment the relayer transaction counter."""

        self.relayer_tx_count += 1

    def snapshot(self) -> MetricsSnapshot:
        """Return a MetricsSnapshot suitable for the web dashboard."""

        today = datetime.utcnow()
        return MetricsSnapshot(
            date=today,
            relayer_tx_count=self.relayer_tx_count,
            relayer_tx_limit=self.relayer_tx_limit,
            volume_by_market=dict(self.volume_by_market),
            markets_traded=len(self.markets_traded),
            strategies_activity=dict(self.strategies_activity),
        )

    def persist_daily_metrics(self, day: date | None = None) -> None:
        """
        Persist the current day's aggregate metrics to the database.

        This should be called periodically (e.g., end of day) or when the engine exits.
        """

        day = day or date.today()
        total_volume = sum(self.volume_by_market.values())
        markets_traded = len(self.markets_traded)

        logger.info(
            "Persisting metrics: day=%s relayer_tx=%s volume=%.4f markets_traded=%s",
            day,
            self.relayer_tx_count,
            total_volume,
            markets_traded,
        )

        with session_scope() as session:
            metric = Metric(
                day=day,
                relayer_tx_count=self.relayer_tx_count,
                volume=total_volume,
                markets_traded=markets_traded,
            )
            session.add(metric)

