# Strategies

This document describes the built-in strategies included in
`polymarket-liquidity-bot-suite`, their configuration, and risk profiles.


## Strategy base class

All strategies inherit from `polymarket_bot.strategies.base.BaseStrategy`. The base
class defines the interface the engine relies on:

- **`on_market_data(market, order_book, positions, now)`**
  - Called whenever new market data is available.
  - Strategies update their internal state here.

- **`on_fill(fill_event)`**
  - Called when an order is filled or partially filled.
  - Strategies can adjust inventory or risk based on fills.

- **`generate_orders()`**
  - Returns a list of desired orders (create/modify/cancel) to send to the CLOB.

Each strategy receives a configuration object (dict or dataclass-like) with:

- Per-strategy risk limits.
- Per-market parameters.
- Operational flags (e.g., enable/disable).

The engine and `RiskManager` validate all orders produced by strategies before
they are submitted.


## Market-making spread tightener

Module: `polymarket_bot.strategies.mm_spread_tightener`

### Concept

This strategy provides **basic two-sided market making** by quoting around the
mid-price of each configured market. It aims to:

- Maintain both bid and ask orders to provide depth.
- Keep spreads relatively tight when:
  - Market liquidity is thin.
  - Inventory is balanced.
- Widen spreads when:
  - Inventory is skewed (overexposed on one side).
  - Volatility or risk conditions suggest caution.

### Inputs and parameters

Typical parameters (see `docs/configuration.md` for examples):

- **`markets`**
  - List of market IDs and per-market spread settings.
- **`quote_size`**
  - Target size per quote (e.g., in USDC).
- **`min_spread_bps` / `max_spread_bps`**
  - Minimum and maximum spreads in basis points.
- **`inventory_skew_sensitivity`**
  - How aggressively spreads widen when inventory is imbalanced.
- **`max_position_per_market`**
  - Upper bound on absolute inventory for each market.

### Risk profile

- Inventory is actively managed:
  - Strategy widens spreads into the direction of existing inventory.
  - Eventually reduces exposure as the market trades against wider quotes.
- Configured caps ensure:
  - No single market accumulates excessive position size.
  - Engine-level limits prevent aggregate exposure or PnL drawdown breaches.


## Volatility rebalancer

Module: `polymarket_bot.strategies.volatility_rebalancer`

### Concept

This strategy **adjusts positions based on recent realized volatility and price
trends**. It is intentionally simple and deterministic:

- Computes volatility over a configurable lookback window.
- If volatility exceeds a threshold:
  - Increases or decreases positions to lean into or fade recent moves (depending on config).
- If volatility is low:
  - Reduces positions toward a neutral baseline.

This is **not** a high-frequency strategy; it is designed for moderate cadence
(e.g., minutes) and clear behavior.

### Inputs and parameters

- **`markets`**
  - List of markets with:
    - `lookback_minutes`
    - `volatility_threshold`
- **`target_position_scale`**
  - Scales the size of positions taken when volatility is high.
- **`max_trade_size`**
  - Hard cap on order sizes to avoid large sudden moves.

### Risk profile

- Focused on **relative position sizing**, not raw price prediction.
- Built-in constraints:
  - Never exceeds `max_trade_size` per adjustment.
  - Uses engine-level limits for total notional exposure and daily drawdown.
- Easy to simulate and backtest in **dry-run mode** by feeding in historical
market data and comparing behavior.


## Signal executor

Module: `polymarket_bot.strategies.signal_executor`

### Concept

The signal executor **translates simple external signals into orders**. Signals
can come from:

- A CSV file periodically reloaded from disk.
- A REST endpoint returning JSON signals.
- A mocked ML model or script for testing.

Typical signals per market might include:

- `direction` – `long`, `short`, or `flat`.
- `confidence` – 0.0–1.0 scaling factor for size.
- `expiry` – optional timestamp after which signal is ignored.

The strategy’s main job is to:

- Read signals at a configured cadence.
- Map them into per-market target positions or one-off trades.
- Respect per-market risk limits and global engine constraints.

### Inputs and parameters

- **`signal_source`**
  - `kind`: `"csv"`, `"rest"`, or `"mock"`.
  - `path` or `url`: where to load signals from.
  - `refresh_interval_seconds`: how often to reload.
- **`default_size`**
  - Baseline trade size when `confidence` is 1.0.
- **`max_position_per_market`**
  - Cap on inventory magnitude per market.

### Risk profile

- The strategy is **bounded by configuration**:
  - Caps on per-signal sizes.
  - Caps on per-market positions.
  - Engine-level global caps.
- Execution can be run in `--dry-run` mode to validate signal behavior without
any live orders being submitted.


## Adding custom strategies

To add a new strategy:

1. Create a new module in `polymarket_bot/strategies/`, e.g.
   `my_custom_strategy.py`.
2. Implement a class inheriting from `BaseStrategy`:
   - Define an appropriate configuration schema.
   - Implement `on_market_data`, `on_fill`, and `generate_orders`.
3. Register the strategy in:
   - The engine’s strategy factory (e.g., a mapping from `type` string to class).
   - Any CLI helper that lists or validates strategies.
4. Document the strategy’s purpose and risk profile in this file or a separate
section.


## Testing strategies

Unit tests in `tests/test_strategies.py` cover:

- Deterministic responses to simplified market data.
- Handling of edge cases (e.g., missing mid-price, zero liquidity).
- Enforcement of per-strategy risk limits.

You can also:

- Run strategies in `--dry-run` mode against:
  - Recorded historical data.
  - Synthetic/mock market scenarios.
- Inspect logs, metrics, and the web dashboard to verify that:
  - Orders are being generated as expected.
  - Risk constraints are respected.

