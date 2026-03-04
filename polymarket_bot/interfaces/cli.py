from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from ..config import get_settings
from ..logging_config import configure_logging, get_logger
from ..polymarket.client import PolymarketClient
from ..storage.db import Metric, session_scope
from ..engine.scheduler import run_strategies
from ..strategies.base import StrategyConfig
from ..strategies.mm_spread_tightener import MMConfig, SpreadTightenerStrategy
from ..strategies.signal_executor import SignalConfig, SignalExecutorStrategy, SignalSourceConfig
from ..strategies.volatility_rebalancer import (
    VolatilityConfig,
    VolatilityMarketParams,
    VolatilityRebalancerStrategy,
)

app = typer.Typer(help="Polymarket liquidity bot CLI.")
logger = get_logger(__name__)


def _load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _strategy_from_config_path(path: Path):
    cfg = _load_yaml(path).get("strategy", {})
    s_type = cfg.get("type")
    name = cfg.get("name", s_type)
    markets = [m["market_id"] for m in cfg.get("markets", [])]
    base = StrategyConfig(
        name=name,
        markets=markets,
        max_position_per_market=float(cfg.get("max_position_per_market", 500.0)),
        max_order_size=float(cfg.get("max_order_size", 100.0)),
    )

    if s_type == "mm_spread_tightener":
        params = {
            m["market_id"]: {
                "min_spread_bps": float(m.get("min_spread_bps", 50.0)),
                "max_spread_bps": float(m.get("max_spread_bps", 200.0)),
            }
            for m in cfg.get("markets", [])
        }
        mm_config = MMConfig(
            name=base.name,
            markets=base.markets,
            max_position_per_market=base.max_position_per_market,
            max_order_size=base.max_order_size,
            quote_size=float(cfg.get("quote_size", 50.0)),
            inventory_skew_sensitivity=float(cfg.get("inventory_skew_sensitivity", 0.5)),
            per_market_params={},  # simplified; see docs for custom params
        )
        return SpreadTightenerStrategy(mm_config)

    if s_type == "volatility_rebalancer":
        per_market_params = {
            m["market_id"]: VolatilityMarketParams(
                market_id=m["market_id"],
                lookback_minutes=int(m.get("lookback_minutes", 60)),
                volatility_threshold=float(m.get("volatility_threshold", 0.1)),
            )
            for m in cfg.get("markets", [])
        }
        v_config = VolatilityConfig(
            name=base.name,
            markets=base.markets,
            max_position_per_market=base.max_position_per_market,
            max_order_size=base.max_order_size,
            target_position_scale=float(cfg.get("target_position_scale", 1.0)),
            max_trade_size=float(cfg.get("max_trade_size", 100.0)),
            per_market_params=per_market_params,
        )
        return VolatilityRebalancerStrategy(v_config)

    if s_type == "signal_executor":
        source_cfg = cfg.get("signal_source", {})
        s_config = SignalConfig(
            name=base.name,
            markets=base.markets,
            max_position_per_market=base.max_position_per_market,
            max_order_size=base.max_order_size,
            signal_source=SignalSourceConfig(
                kind=source_cfg.get("kind", "csv"),
                path=source_cfg.get("path"),
                url=source_cfg.get("url"),
                refresh_interval_seconds=int(source_cfg.get("refresh_interval_seconds", 30)),
            ),
            default_size=float(cfg.get("default_size", 50.0)),
        )
        return SignalExecutorStrategy(s_config)

    raise typer.BadParameter(f"Unknown strategy type '{s_type}' in {path}")


@app.callback()
def main(  # type: ignore[override]
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """Configure logging before commands run."""

    configure_logging()
    if verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)


@app.command()
def init_config(
    output_dir: Path = typer.Argument(Path("./config"), help="Directory for config files."),
) -> None:
    """
    Generate example YAML configs for built-in strategies.
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    mm_example = {
        "strategy": {
            "type": "mm_spread_tightener",
            "name": "mm-spread-tightener",
            "markets": [
                {
                    "market_id": "example-market-1",
                    "min_spread_bps": 50,
                    "max_spread_bps": 200,
                }
            ],
            "quote_size": 50.0,
            "max_position_per_market": 500.0,
            "inventory_skew_sensitivity": 0.5,
        }
    }
    (output_dir / "mm_spread_tightener.example.yaml").write_text(yaml.safe_dump(mm_example))

    vol_example = {
        "strategy": {
            "type": "volatility_rebalancer",
            "name": "volatility-rebalancer",
            "markets": [
                {
                    "market_id": "example-market-2",
                    "lookback_minutes": 60,
                    "volatility_threshold": 0.1,
                }
            ],
            "target_position_scale": 1.0,
            "max_trade_size": 100.0,
            "max_position_per_market": 500.0,
        }
    }
    (output_dir / "volatility_rebalancer.example.yaml").write_text(yaml.safe_dump(vol_example))

    signal_example = {
        "strategy": {
            "type": "signal_executor",
            "name": "signal-executor",
            "markets": [
                {
                    "market_id": "example-market-3",
                }
            ],
            "signal_source": {
                "kind": "csv",
                "path": "./signals/example_signals.csv",
                "refresh_interval_seconds": 30,
            },
            "default_size": 50.0,
            "max_position_per_market": 300.0,
        }
    }
    (output_dir / "signal_executor.example.yaml").write_text(yaml.safe_dump(signal_example))

    typer.echo(f"Example configs written to {output_dir}")


@app.command()
def run_strategy(
    strategy: str = typer.Argument(..., help="Strategy config file name (without path)."),
    config_dir: Path = typer.Option(Path("./config"), help="Directory containing config files."),
    interval_seconds: float = typer.Option(
        5.0,
        "--interval",
        help="Polling interval in seconds.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate trading without sending orders.",
    ),
) -> None:
    """
    Run a specific strategy with the given config.
    """

    path = config_dir / strategy
    if not path.exists():
        raise typer.BadParameter(f"Config file not found: {path}")

    strat = _strategy_from_config_path(path)
    run_strategies([strat], interval_seconds=interval_seconds, dry_run=dry_run)


@app.command()
def run_all(
    config_dir: Path = typer.Option(Path("./config"), help="Directory containing config files."),
    interval_seconds: float = typer.Option(
        5.0,
        "--interval",
        help="Polling interval in seconds.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate trading without sending orders.",
    ),
) -> None:
    """
    Run all strategy configs found in a directory.
    """

    config_files = sorted(config_dir.glob("*.yaml"))
    if not config_files:
        typer.echo(f"No strategy configs found in {config_dir}")
        raise typer.Exit(code=1)

    strategies = [_strategy_from_config_path(p) for p in config_files]
    run_strategies(strategies, interval_seconds=interval_seconds, dry_run=dry_run)


@app.command()
def show_positions() -> None:
    """
    Print current positions for the configured wallet.
    """

    settings = get_settings()
    if not settings.wallet_address:
        typer.echo("No WALLET_ADDRESS configured in environment.")
        raise typer.Exit(code=1)

    client = PolymarketClient()
    positions = client.fetch_positions(settings.wallet_address)
    typer.echo(json.dumps([p.model_dump() for p in positions], indent=2))


@app.command()
def show_metrics(limit: int = typer.Option(10, help="Number of days to show.")) -> None:
    """
    Print recent daily metrics (relayer tx count, volume, markets traded).
    """

    with session_scope() as session:
        rows = (
            session.query(Metric)
            .order_by(Metric.day.desc())
            .limit(limit)
            .all()
        )
        data = [
            {
                "day": m.day.isoformat(),
                "relayer_tx_count": m.relayer_tx_count,
                "volume": m.volume,
                "markets_traded": m.markets_traded,
            }
            for m in rows
        ]
        typer.echo(json.dumps(data, indent=2))


@app.command()
def web(
    host: Optional[str] = typer.Option(None, help="Host to bind the web server to."),
    port: Optional[int] = typer.Option(None, help="Port for the web server."),
) -> None:
    """
    Start the FastAPI web dashboard.
    """

    from .webapp.main import create_app
    import uvicorn

    settings = get_settings()
    app_instance = create_app()
    uvicorn.run(
        app_instance,
        host=host or settings.web_host,
        port=port or settings.web_port,
    )

