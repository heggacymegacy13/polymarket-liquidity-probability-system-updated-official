from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings, get_settings
from ..logging_config import get_logger
from ..polymarket.models import Order

logger = get_logger(__name__)


@dataclass
class StrategyLimits:
    """Per-strategy risk limits."""

    name: str
    max_order_size: float
    max_position_per_market: float


class RiskManager:
    """
    Enforces global and per-strategy risk limits.

    This includes:
    - Max notional exposure per market.
    - Max total exposure.
    - Max daily PnL drawdown (hook for future extension).
    - Per-strategy caps (max order size, max market exposure).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def check_order(
        self,
        strategy_limits: StrategyLimits,
        order: Order,
        current_market_notional: float,
        current_total_notional: float,
    ) -> bool:
        """
        Validate whether an order is allowed under current risk limits.

        Returns True if the order is permitted, False otherwise.
        """

        proposed_notional = order.price * abs(order.size)
        logger.debug(
            "Risk check: strategy=%s market=%s size=%.4f price=%.4f current_market_notional=%.4f",
            strategy_limits.name,
            order.market_id,
            order.size,
            order.price,
            current_market_notional,
        )

        if abs(order.size) > strategy_limits.max_order_size:
            logger.warning(
                "Order rejected: size %.4f exceeds per-strategy max_order_size %.4f",
                abs(order.size),
                strategy_limits.max_order_size,
            )
            return False

        if current_market_notional + proposed_notional > self.settings.risk.max_market_notional:
            logger.warning(
                "Order rejected: market notional would exceed max_market_notional (%.4f > %.4f)",
                current_market_notional + proposed_notional,
                self.settings.risk.max_market_notional,
            )
            return False

        if current_total_notional + proposed_notional > self.settings.risk.max_daily_notional:
            logger.warning(
                "Order rejected: total notional would exceed max_daily_notional (%.4f > %.4f)",
                current_total_notional + proposed_notional,
                self.settings.risk.max_daily_notional,
            )
            return False

        # Hook: daily drawdown checks can be implemented here using PnL tracking.

        return True

