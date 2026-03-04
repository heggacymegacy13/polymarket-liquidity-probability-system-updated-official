from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from ...config import get_settings
from ...engine.metrics import MetricsCollector
from ...logging_config import configure_logging, get_logger
from ...polymarket.client import PolymarketClient
from ...polymarket.models import Position
from ...storage.db import Metric, session_scope

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""

    configure_logging()
    app = FastAPI(title="Polymarket Liquidity Bot Dashboard")

    templates = Jinja2Templates(
        directory=str(Path(__file__).parent / "templates"),
    )

    @app.get("/", response_class=HTMLResponse)
    async def overview(request: Request) -> Any:
        settings = get_settings()
        client = PolymarketClient()
        positions: List[Position] = []
        if settings.wallet_address:
            positions = client.fetch_positions(settings.wallet_address)

        with session_scope() as session:
            latest_metric = (
                session.query(Metric)
                .order_by(Metric.day.desc())
                .first()
            )

        metrics_data: Dict[str, Any] | None = None
        if latest_metric:
            metrics_data = {
                "day": latest_metric.day.isoformat(),
                "relayer_tx_count": latest_metric.relayer_tx_count,
                "volume": latest_metric.volume,
                "markets_traded": latest_metric.markets_traded,
            }

        return templates.TemplateResponse(
            "overview.html",
            {
                "request": request,
                "positions": positions,
                "metrics": metrics_data,
            },
        )

    @app.get("/markets", response_class=HTMLResponse)
    async def markets(request: Request) -> Any:
        client = PolymarketClient()
        markets = client.fetch_markets()
        return templates.TemplateResponse(
            "markets.html",
            {
                "request": request,
                "markets": markets,
            },
        )

    @app.get("/metrics", response_class=HTMLResponse)
    async def metrics(request: Request) -> Any:
        with session_scope() as session:
            rows = (
                session.query(Metric)
                .order_by(Metric.day.desc())
                .limit(30)
                .all()
            )
        return templates.TemplateResponse(
            "metrics.html",
            {
                "request": request,
                "rows": rows,
            },
        )

    @app.get("/metrics/prometheus", response_class=PlainTextResponse)
    async def prometheus_metrics() -> str:
        """
        Very simple Prometheus text-format metrics endpoint.

        For a full integration, extend this to expose per-strategy metrics and more
        granular data.
        """

        today = date.today()
        with session_scope() as session:
            m = (
                session.query(Metric)
                .filter(Metric.day == today)
                .first()
            )
        relayer_tx = m.relayer_tx_count if m else 0
        volume = m.volume if m else 0.0
        return (
            "# HELP polymarket_relayer_tx_today Number of relayer transactions today\n"
            "# TYPE polymarket_relayer_tx_today gauge\n"
            f"polymarket_relayer_tx_today {relayer_tx}\n"
            "# HELP polymarket_volume_today Total notional volume today\n"
            "# TYPE polymarket_volume_today gauge\n"
            f"polymarket_volume_today {volume}\n"
        )

    return app

