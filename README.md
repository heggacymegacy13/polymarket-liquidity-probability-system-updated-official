polymarket-liquidity-bot-suite
================================

An opinionated, production-grade reference implementation of a **Polymarket Builder trading system**.

This repository provides a modular framework for:

- **Polymarket integration**: Markets, events, order books, positions, trades.
- **Builder attribution**: Builder signing and headers on all CLOB traffic.
- **Relayer & gasless trading**: Proxy/safe wallet handling and transaction limits.
- **Strategy engine**: Pluggable strategies (market making, volatility, signals).
- **Interfaces**: A Typer-based CLI and a minimal FastAPI dashboard.

The goal is to clearly demonstrate a realistic path to **Verified Builder (3,000 tx/day)** by:

- Tracking **daily relayer transactions** and volume.
- Running multiple strategies and markets concurrently.
- Enforcing **risk limits** so scale is safe and controlled.

> **Note**  
> This is a reference implementation. You must plug in the official Polymarket Builder Program details (endpoints, signing rules, and relayer behavior) before trading with real funds.


## Repository layout

The project is structured as a serious, multi-module codebase:

- **Project root**
  - `pyproject.toml` – installable Python package, tooling (black, ruff, mypy).
  - `.env.example` – environment variables for Polymarket, Builder, Relayer, DB.
  - `Dockerfile`, `docker-compose.yml` – local deployment for bot + web UI + DB.
  - `scripts/` – helper scripts to run the bot, dev server, and seed example configs.
  - `docs/` – architecture, configuration, strategy, and deployment documentation.
- **Package**
  - `polymarket_bot/` – core SDK, strategies, engine, interfaces, storage.
    - `polymarket/` – client, models, auth, relayer, CLOB.
    - `strategies/` – base class + market making, volatility rebalancing, signal executor.
    - `engine/` – scheduler, execution engine, risk, portfolio, metrics.
    - `interfaces/` – Typer CLI and FastAPI dashboard.
    - `storage/` – DB integration (SQLite/Postgres) for metrics and state.


## Getting started

### 1. Install

This project targets **Python 3.11+**.

```bash
pip install -e .
```

Or with `poetry`:

```bash
poetry install
```


### 2. Configure

1. Copy `.env.example` to `.env` and fill in the required values:
   - `POLYMARKET_API_BASE`
   - `BUILDER_API_KEY`, `BUILDER_API_SECRET`
   - `RELAYER_API_KEY`
   - `DATABASE_URL`, etc.
2. Optionally create strategy config files (YAML/JSON) as described in `docs/configuration.md`.

You can also use the CLI to scaffold base configs:

```bash
polymarket-bot init-config
```


### 3. Run a basic strategy

Run a single strategy (e.g. spread-tightening market maker) against your configured markets:

```bash
polymarket-bot run-strategy mm-spread-tightener --config ./config/mm_spread_tightener.example.yaml
```

Run all enabled strategies:

```bash
polymarket-bot run-all
```

Use `--dry-run` on any run command to simulate trading and just log hypothetical orders:

```bash
polymarket-bot run-all --dry-run
```


### 4. Web dashboard

Start the web dashboard (FastAPI + Jinja templates):

```bash
polymarket-bot web
```

Or via the helper script:

```bash
scripts/run_dev_server.sh
```

The default URL is `http://localhost:8000`.

Dashboard pages:

- **Overview** – current positions, recent trades, PnL.
- **Markets** – watched markets and a basic order book snapshot.
- **Metrics** – daily transaction count, daily volume, per-strategy stats.


## Polymarket Builder Integration

This project is built around the **Polymarket Builder Program**:

- **CLOB client** (`polymarket/client.py`, `polymarket/clob.py`)
  - Fetches markets, events, order books, positions, and trades.
  - Constructs, signs, and submits builder-attributed limit orders.
- **Builder signing & attribution** (`polymarket/auth.py`)
  - Centralized signing utilities for HTTP and WebSocket messages.
  - Injects the correct builder headers into CLOB and relayer calls.
- **Relayer client** (`polymarket/relayer.py`)
  - Integrates with the Builder Program relayer for **gasless** operations.
  - Supports proxy/safe wallets, token approvals, and CTF wrappers (split/merge/redeem).
- **Transaction limits & metrics** (`engine/metrics.py`, web dashboard)
  - Tracks **“Relayer transactions today”** vs a configurable daily cap.
  - Records volume, markets traded, and per-strategy activity.

> The concrete endpoint URLs, parameter schemas, and signing rules are factored out into
> configuration and small utility functions so they can be aligned 1:1 with the official
> Polymarket documentation.


## Why this project benefits Polymarket liquidity

- **Continuous two-sided quotes**
  - Ships a market-making engine designed to maintain both bid and ask quotes on many markets.
  - Tightens spreads when liquidity is thin, increasing depth where it is most useful.
- **Better user experience**
  - Lower slippage and tighter spreads make it easier for users to trade informed views.
  - Positions and PnL are tracked so builders can monitor and manage risk responsibly.
- **Aligned with Builder Program mechanisms**
  - Uses the official Builder Program primitives: CLOB client, relayer, and builder attribution.
  - Makes attribution explicit, making it easy for Polymarket to attribute volume correctly.
- **Extensible by other builders**
  - Modular SDK + strategies + engine architecture.
  - Clear docs and examples for building custom strategies on top of the same core.


## Verified tier justification

This repository is explicitly designed to **earn and justify Verified Builder status**:

- **High, trackable throughput**
  - `engine/metrics.py` tracks:
    - Daily relayer transaction count.
    - Volume by day and week.
    - Number of markets traded and strategy-level stats.
  - The web dashboard prominently displays:
    - **“Relayer transactions today”** vs configured daily limits.
    - Per-strategy transaction and volume breakdown.
- **Safe scaling**
  - `engine/risk.py` enforces:
    - Global notional limits per market.
    - Total portfolio exposure caps.
    - Max daily PnL drawdown.
  - Strategies declare their own risk parameters and respect global caps.
- **Operational readiness**
  - CLI commands for configuration, running strategies, and inspecting positions/metrics.
  - Docker-based deployment for running bots and dashboard in production.
  - Logging, basic observability, and persistence of metrics in a database backend.

Under normal operation across multiple active markets, this system is intended to
**comfortably exceed 100 relayer transactions per day**. With conservative parameters,
multiple strategies, and multi-market operation enabled, it can naturally reach the
**3,000 tx/day** target that Verified Builders are expected to sustain.


## Development

- **Tooling**
  - Formatting: `black`
  - Linting: `ruff`
  - Type checking: `mypy`
  - Tests: `pytest`
- **Pre-commit**
  - A `.pre-commit-config.yaml` is provided to run formatting and linting before every commit.

Typical development loop:

```bash
pip install -e ".[dev]"
pre-commit install
pytest
```

See `docs/architecture.md`, `docs/configuration.md`, `docs/strategies.md`,
and `docs/deployment.md` for deeper details.

