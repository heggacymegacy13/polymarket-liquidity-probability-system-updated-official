# Architecture

This document describes the high-level architecture of `polymarket-liquidity-bot-suite`:
its modules, data flow, and execution model.


## Overview

The system is organized into five main layers:

1. **Polymarket SDK (`polymarket_bot.polymarket`)**
   - Typed client for Polymarket REST/WebSocket APIs.
   - Pydantic models for markets, events, outcomes, orders, trades, and positions.
   - Builder authentication, relayer integration, and CLOB order construction.
2. **Strategy layer (`polymarket_bot.strategies`)**
   - Base strategy interface.
   - Concrete market making, volatility, and signal-following strategies.
3. **Engine (`polymarket_bot.engine`)**
   - Scheduler, execution loop, risk controls, portfolio tracking, and metrics.
4. **Interfaces (`polymarket_bot.interfaces`)**
   - Typer CLI (`cli.py`) for operational control.
   - FastAPI web dashboard (`webapp/`) for monitoring and manual inspection.
5. **Storage (`polymarket_bot.storage`)**
   - Database connections and schema/migrations for metrics and state.


## Data flow

1. **Market data ingress**
   - `polymarket_bot.polymarket.client.PolymarketClient` fetches:
     - Markets and events.
     - Order books / depth snapshots.
     - User positions and balances.
   - Data is converted into Pydantic models from `polymarket_bot.polymarket.models`.

2. **Strategy evaluation**
   - The `ExecutionEngine` (in `engine/execution.py`) subscribes to relevant markets
     via polling or streaming.
   - For each incoming market snapshot:
     - It calls `strategy.on_market_data(...)`.
     - The strategy updates its internal state and, when appropriate, implements logic
       in `generate_orders(...)` to produce desired orders.

3. **Risk & portfolio checks**
   - Before submission, proposed orders are passed through:
     - `RiskManager` (`engine/risk.py`) for global and per-strategy constraints.
     - `Portfolio` (`engine/portfolio.py`) for exposure and mark-to-market checks.
   - Orders that violate limits are rejected or truncated.

4. **Execution & relayer**
   - Approved orders are sent to `polymarket_bot.polymarket.clob` which:
     - Builds the correct CLOB order structures.
     - Signs and attributes orders using `auth.BuilderAuth`.
     - Submits orders via HTTP/WS using `PolymarketClient`.
   - For gasless execution, `RelayerClient` (`polymarket/relayer.py`) is used to:
     - Deploy or manage proxy/safe wallets.
     - Approve USDC or outcome tokens.
     - Relay orders and CTF operations.

5. **Metrics & persistence**
   - Fills and order submissions are recorded by `MetricsCollector` (`engine/metrics.py`):
     - Daily transaction count (with a focus on relayer tx).
     - Volume per day/week.
     - Markets traded and per-strategy stats.
   - Metrics are stored via `storage/db.py` into SQLite/Postgres.
   - The web dashboard reads from both in-memory metrics and the DB.


## Execution and scheduling model

The engine is designed to support both **continuous** and **interval-based** operation:

- **Continuous (event-driven) mode**
  - Ideal when subscribing to a streaming order book or event feed.
  - The engine registers callbacks (or runs a loop) that reacts to new market data.
  - Strategies are invoked as soon as fresh data arrives, subject to rate limits.

- **Interval (cron-like) mode**
  - Configurable through `engine/scheduler.py`.
  - The engine wakes up every N seconds, fetches current market data, and runs all
    configured strategies once.
  - Simpler to reason about and test, appropriate for many Builder use cases.

In both modes:

- Graceful shutdown is supported via:
  - OS signals propagated into a shared `Event`/flag.
  - The engine finishing the current loop iteration and then exiting.
- Restart logic can be implemented outside this process (e.g., via systemd, Docker, or
  a process supervisor).


## Safety and scalability

### Safety: risk controls

Risk management is explicit and centralized:

- **Global limits**
  - Max notional exposure per market.
  - Max total portfolio notional.
  - Max daily PnL drawdown.
- **Per-strategy caps**
  - Each strategy declares:
    - Max size per order.
    - Max open interest per market.
    - Allowed markets or event types.

These constraints are enforced in `RiskManager` and validated on every proposed order
before it can be submitted to the CLOB or relayer.


### Scalability: multi-strategy, multi-market

The engine and data model are intentionally designed to scale:

- **Multi-strategy**
  - Multiple strategies can run concurrently over:
    - Distinct sets of markets.
    - Overlapping markets with different risk and inventory profiles.
  - Per-strategy metrics and configuration allow for independent tuning.

- **Multi-market**
  - The client and models are generic over markets and outcomes.
  - Strategies are written in terms of market identifiers and outcomes, not hard-coded IDs.
  - The engine can fan out over many markets with shared data-fetching and throttling.


## Module overview

- `polymarket_bot/config.py`
  - Central configuration using environment variables and optional YAML/JSON files.
  - Provides typed access to:
    - API endpoints and keys.
    - Risk parameters.
    - Scheduler cadence.

- `polymarket_bot/logging_config.py`
  - Configures structured logging for:
    - Engine decisions.
    - Strategy actions.
    - Metrics and errors.

- `polymarket_bot/polymarket/models.py`
  - Pydantic models for:
    - `Market`, `Event`, `Outcome`
    - `Order`, `Trade`, `Position`
  - Each field is documented in terms of Polymarket’s “Markets & Events” semantics.

- `polymarket_bot/polymarket/client.py`
  - HTTP client built on `httpx` (sync or async).
  - Fetch methods for markets, events, order books, positions, balances, and recent trades.

- `polymarket_bot/polymarket/auth.py`
  - Builder Program signing utilities and header construction.
  - Reads keys from env/config and applies them consistently.

- `polymarket_bot/polymarket/relayer.py`
  - Relayer integration for gasless transactions:
    - Wallet deployment/management.
    - Token approvals.
    - CTF wrappers for split/merge/redeem.

- `polymarket_bot/polymarket/clob.py`
  - Functions and classes for:
    - Building CLOB limit orders.
    - Calculating mid-price, spreads, and tick/precision handling.
    - Submitting, modifying, and canceling orders.

- `polymarket_bot/strategies/base.py`
  - Abstract base class with:
    - `on_market_data(...)`
    - `on_fill(...)`
    - `generate_orders(...)`
  - Strategy-level config and limits.

- `polymarket_bot/strategies/mm_spread_tightener.py`
  - Market-making strategy focused on:
    - Quoting around mid-price.
    - Tightening spreads when liquidity is thin.
    - Widening spreads when inventory is imbalanced.

- `polymarket_bot/strategies/volatility_rebalancer.py`
  - Adjusts positions based on recent volatility and price changes.
  - Simple rule-based logic for clarity and determinism.

- `polymarket_bot/strategies/signal_executor.py`
  - Executes long/short signals derived from:
    - CSV files.
    - REST endpoints.
    - Mocked ML models.

- `polymarket_bot/engine/execution.py`
  - `ExecutionEngine` orchestrates data fetching, strategy invocation, risk checks,
    order submission, and metrics collection.

- `polymarket_bot/engine/scheduler.py`
  - Cron-like or continuous loop around the execution engine.

- `polymarket_bot/engine/risk.py`
  - Global and per-strategy risk enforcement.

- `polymarket_bot/engine/portfolio.py`
  - Tracks positions per outcome and mark-to-market PnL.

- `polymarket_bot/engine/metrics.py`
  - Tracks:
    - Daily transaction count (with a critical focus on relayer tx).
    - Volume per day/week.
    - Markets traded.
    - Maker/taker breakdown where available.
  - Exposes metrics via logs and the database, and is consumed by the web UI.

- `polymarket_bot/interfaces/cli.py`
  - Typer CLI with commands for:
    - `init-config`
    - `run-strategy`
    - `run-all`
    - `show-positions`
    - `show-metrics`
    - `web` (start dashboard)

- `polymarket_bot/interfaces/webapp/main.py`
  - FastAPI app providing:
    - Overview, markets, and metrics pages.
    - Optional Prometheus metrics endpoint.

- `polymarket_bot/storage/db.py`
  - Database session factories for SQLite/Postgres.
  - Metrics and optional positions/trades schema.


## Notes on Polymarket integration

- Concrete API paths, parameters, and signing rules are intentionally abstracted into
  small, replaceable components.
- When integrating with the live Builder Program:
  - Replace stubbed endpoints and field names with the official ones.
  - Tighten types in the Pydantic models based on the actual API schema.
  - Add any additional models (e.g., settlement events) as needed.

