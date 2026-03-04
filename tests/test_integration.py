from __future__ import annotations

from polymarket_bot.engine.metrics import MetricsCollector


def test_integration_metrics_persistence_smoke() -> None:
    """
    Smoke test for metrics persistence pipeline.

    This does not hit real APIs; it just verifies that the metrics collector
    can persist a daily record without raising.
    """

    from polymarket_bot.storage.db import init_db

    init_db()
    mc = MetricsCollector()
    mc.record_order_submission("s1", "m1", 42.0)
    mc.record_relayer_tx()
    mc.persist_daily_metrics()

