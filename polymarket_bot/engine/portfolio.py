from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from ..polymarket.models import Position


Key = Tuple[str, str]  # (market_id, outcome_id)


@dataclass
class Portfolio:
    """
    In-memory portfolio tracking for outcome tokens.

    This class is intentionally lightweight and is used by the engine to enforce
    exposure limits and compute basic mark-to-market PnL when combined with prices.
    """

    positions: Dict[Key, Position] = field(default_factory=dict)

    def update_from_positions(self, positions: list[Position]) -> None:
        """Replace internal state with the given list of positions."""

        self.positions = {(p.market_id, p.outcome_id): p for p in positions}

    def apply_fill(
        self,
        market_id: str,
        outcome_id: str,
        size_delta: float,
        fill_price: float,
    ) -> None:
        """
        Update portfolio based on a new fill.

        size_delta > 0 for net buy, < 0 for net sell.
        """

        key: Key = (market_id, outcome_id)
        current = self.positions.get(
            key,
            Position(
                market_id=market_id,
                outcome_id=outcome_id,
                size=0.0,
                avg_entry_price=None,
                unrealized_pnl=None,
            ),
        )

        new_size = current.size + size_delta
        if current.avg_entry_price is None or current.size == 0:
            new_avg_price = fill_price
        else:
            notional = current.avg_entry_price * current.size + fill_price * size_delta
            if new_size != 0:
                new_avg_price = notional / new_size
            else:
                new_avg_price = None

        updated = Position(
            market_id=market_id,
            outcome_id=outcome_id,
            size=new_size,
            avg_entry_price=new_avg_price,
            unrealized_pnl=None,
        )
        self.positions[key] = updated

    def total_notional(self, prices: dict[Key, float]) -> float:
        """Compute total portfolio notional given a mapping of prices."""

        total = 0.0
        for key, pos in self.positions.items():
            price = prices.get(key)
            if price is None:
                continue
            total += abs(pos.size) * price
        return total

