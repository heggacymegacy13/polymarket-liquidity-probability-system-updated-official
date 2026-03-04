"""
polymarket_bot
================

Core package for the Polymarket liquidity bot suite.

This package exposes:

- Configuration and logging helpers.
- A typed Polymarket SDK (client, models, auth, relayer, CLOB).
- Strategy interfaces and built-in strategies.
- Execution engine, risk controls, portfolio tracking, and metrics.
- CLI and web dashboard entry points.
"""

from .config import Settings, get_settings  # noqa: F401

