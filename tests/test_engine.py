from __future__ import annotations

from polymarket_bot.engine.metrics import MetricsCollector


def test_metrics_collector_records_and_snapshots() -> None:
    mc = MetricsCollector(relayer_tx_limit=100)
    mc.record_order_submission("s1", "m1", 10.0)
    mc.record_relayer_tx()
    snap = mc.snapshot()
    assert snap.relayer_tx_count == 1
    assert snap.relayer_tx_limit == 100
    assert snap.volume_by_market["m1"] == 10.0

