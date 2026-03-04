from __future__ import annotations

from typing import Iterable

from ..logging_config import get_logger
from ..strategies.base import BaseStrategy
from .execution import ExecutionEngine

logger = get_logger(__name__)


def run_strategies(
    strategies: Iterable[BaseStrategy],
    interval_seconds: float = 5.0,
    dry_run: bool = False,
) -> None:
    """
    Convenience function to run a set of strategies with a shared engine.

    This is what the CLI entrypoints call.
    """

    engine = ExecutionEngine(strategies=strategies, dry_run=dry_run)
    logger.info(
        "Running %d strategies (interval=%ss, dry_run=%s)",
        len(list(strategies)),
        interval_seconds,
        dry_run,
    )
    engine.run_forever(interval_seconds=interval_seconds)

