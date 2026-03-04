from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskSettings(BaseModel):
    """Global and per-day risk parameters for the engine."""

    max_daily_tx: int = Field(3000, description="Maximum relayer transactions per day.")
    max_daily_notional: float = Field(
        100_000.0, description="Maximum notional exposure across all markets."
    )
    max_market_notional: float = Field(
        25_000.0, description="Maximum notional exposure per single market."
    )
    max_daily_drawdown: float = Field(
        5_000.0, description="Maximum allowed daily PnL drawdown before halting trading."
    )


class Settings(BaseSettings):
    """Top-level configuration loaded from environment variables (.env)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Polymarket API
    polymarket_api_base: str = Field(
        "https://api.polymarket.com", alias="POLYMARKET_API_BASE", description="Polymarket API base."
    )

    # Builder Program
    builder_api_key: Optional[str] = Field(
        None, alias="BUILDER_API_KEY", description="Polymarket Builder API key."
    )
    builder_api_secret: Optional[str] = Field(
        None, alias="BUILDER_API_SECRET", description="Polymarket Builder API secret."
    )

    # Relayer
    relayer_api_base: str = Field(
        "https://relayer.polymarket.com",
        alias="RELAYER_API_BASE",
        description="Relayer API base URL.",
    )
    relayer_api_key: Optional[str] = Field(
        None, alias="RELAYER_API_KEY", description="Relayer API key."
    )

    # Wallet / signing
    private_key: Optional[str] = Field(None, alias="PRIVATE_KEY")
    wallet_address: Optional[str] = Field(None, alias="WALLET_ADDRESS")

    # Database
    database_url: str = Field(
        "sqlite:///./polymarket_metrics.db",
        alias="DATABASE_URL",
        description="Database URL for metrics and state.",
    )

    # Risk
    risk: RiskSettings = Field(default_factory=RiskSettings)

    # Web
    web_host: str = Field("0.0.0.0", alias="WEB_HOST")
    web_port: int = Field(8000, alias="WEB_PORT")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()  # type: ignore[arg-type]

