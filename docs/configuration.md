# Configuration

This document describes how to configure `polymarket-liquidity-bot-suite` via
environment variables and optional strategy configuration files.


## Environment variables

Environment variables are loaded via `python-dotenv` in `polymarket_bot.config`.
Copy `.env.example` to `.env` and adjust values as needed.

### Core Polymarket settings

- **`POLYMARKET_API_BASE`**
  - Base URL for Polymarket APIs (REST/WebSocket).
  - Example: `https://api.polymarket.com`


### Builder Program credentials

- **`BUILDER_API_KEY`**
  - Public key / identifier for your Builder account.
  - Used in request headers for attribution.

- **`BUILDER_API_SECRET`**
  - Secret used to sign Builder-authenticated requests (e.g., HMAC).
  - Keep this value private and never commit it to version control.


### Relayer / gasless trading

- **`RELAYER_API_BASE`**
  - Base URL for the Builder Program relayer.

- **`RELAYER_API_KEY`**
  - API key used to authorize relayer actions (wallet deployment, approvals, relayed txs).


### Wallet / signing

- **`PRIVATE_KEY`**
  - Private key used for signing messages/transactions when applicable.
  - Only required if your integration needs direct wallet signing in addition to Builder signing.

- **`WALLET_ADDRESS`**
  - Primary wallet address for positions and balances.


### Database configuration

- **`DATABASE_URL`**
  - SQLAlchemy-style database URL.
  - Examples:
    - SQLite: `sqlite:///./polymarket_metrics.db`
    - Postgres: `postgresql+psycopg2://user:pass@host:5432/dbname`
  - Used by `polymarket_bot.storage.db` for metrics and optional state.


### Engine and risk defaults

- **`MAX_DAILY_TX`**
  - Integer limit on total transactions per day (relayer-focused).
  - Default in `.env.example` is `3000`.

- **`MAX_DAILY_NOTIONAL`**
  - Maximum notional exposure across all markets in quote currency (e.g., USDC).

- **`MAX_MARKET_NOTIONAL`**
  - Maximum notional exposure per single market.

- **`MAX_DAILY_DRAWDOWN`**
  - Maximum allowed daily PnL drawdown before strategies are halted.


### Web app configuration

- **`WEB_HOST`**
  - Host interface for the FastAPI web server.
  - Example: `0.0.0.0`

- **`WEB_PORT`**
  - Port for the FastAPI web server (string or integer).
  - Example: `8000`


## Strategy configuration files

Strategies accept configuration via Python dictionaries and optional
YAML/JSON files. The typical workflow is:

1. Use the CLI to generate a base config:

   ```bash
   polymarket-bot init-config
   ```

2. Edit the generated config files in a `config/` directory.
3. Pass the config path to `run-strategy` or `run-all`.


### Example: market-making spread tightener

Example YAML (`config/mm_spread_tightener.example.yaml`):

```yaml
strategy:
  type: "mm_spread_tightener"
  markets:
    - market_id: "example-market-1"
      min_spread_bps: 50
      max_spread_bps: 200
  quote_size: 50.0
  max_position_per_market: 500.0
  inventory_skew_sensitivity: 0.5
  refresh_interval_seconds: 10
```

Key fields:

- **`markets`**
  - List of market IDs to quote.
  - Per-market parameters for minimum/maximum spread (basis points).

- **`quote_size`**
  - Default size per quote in base units (e.g., USDC).

- **`max_position_per_market`**
  - Cap on inventory per market for this strategy.

- **`inventory_skew_sensitivity`**
  - Controls how aggressively spreads widen when inventory is imbalanced.


### Example: volatility rebalancer

Example YAML (`config/volatility_rebalancer.example.yaml`):

```yaml
strategy:
  type: "volatility_rebalancer"
  markets:
    - market_id: "example-market-2"
      lookback_minutes: 60
      volatility_threshold: 0.1
  target_position_scale: 1.0
  max_trade_size: 100.0
```

Key fields:

- **`lookback_minutes`**
  - Window of prices used to compute realized volatility.

- **`volatility_threshold`**
  - Minimum volatility required before the strategy adjusts positions.

- **`target_position_scale`**
  - Multiplier for how strongly to react to volatility.

- **`max_trade_size`**
  - Maximum order size per rebalancing action.


### Example: signal executor

Example YAML (`config/signal_executor.example.yaml`):

```yaml
strategy:
  type: "signal_executor"
  signal_source:
    kind: "csv"
    path: "./signals/example_signals.csv"
    refresh_interval_seconds: 30
  default_size: 50.0
  max_position_per_market: 300.0
```

Key fields:

- **`signal_source`**
  - `kind`: `"csv"` or `"rest"` (or `"mock"` for testing).
  - `path` or `url`: location of signals.
  - `refresh_interval_seconds`: how often to reload signals.

- **`default_size`**
  - Base size per signal execution.

- **`max_position_per_market`**
  - Cap on exposure per market for signal-based trades.


## Engine configuration

Engine-specific options are typically provided via:

- Environment variables (for global behavior).
- CLI flags (e.g., polling intervals).
- Strategy configs (for per-strategy parameters).

Common parameters:

- **Polling interval**
  - How frequently to fetch market data in interval mode.
- **Max concurrent markets**
  - Limit on number of markets the engine processes at once.
- **Dry-run mode**
  - When enabled, orders are logged but not submitted to CLOB/relayer.


## Putting it together

A typical configuration flow for production might be:

1. Provision Builder/Relayer keys and a database.
2. Configure `.env` with:
   - API base URLs.
   - Builder and Relayer keys.
   - Database URL.
   - Global risk caps.
3. Create per-strategy YAML configs in a `config/` directory.
4. Start the engine with:

   ```bash
   polymarket-bot run-all --config-dir ./config
   ```

5. Start the dashboard with:

   ```bash
   polymarket-bot web
   ```

