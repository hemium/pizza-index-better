"""
Centralized configuration management using Pydantic Settings.

Loads configuration from environment variables and optional YAML file.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project paths
    PROJECT_ROOT: Path = Field(default_factory=get_project_root)
    CONFIG_DIR: Path = Field(default_factory=lambda: get_project_root() / "config")
    DATA_DIR: Path = Field(default_factory=lambda: get_project_root() / "data")
    LOG_DIR: Path = Field(default_factory=lambda: get_project_root() / "logs")

    # Pizza Monitor
    PIZZA_API_URL: str = "https://www.pizzint.watch/api/dashboard-data"
    POLL_INTERVAL_MINUTES: int = 5

    # Signal Detection
    DEFCON_THRESHOLD: int = 3  # Alert when DEFCON <= this
    SPIKE_THRESHOLD: int = 2  # Min locations with spikes
    CONFIDENCE_THRESHOLD: float = 0.7
    OFF_HOURS_START: int = 0  # Midnight ET
    OFF_HOURS_END: int = 6  # 6am ET

    # Polymarket
    POLYMARKET_API_URL: str = "https://api.polymarket.com"
    POLYMARKET_GRAPHQL_URL: str = "https://poly-market-events-maker-api.herokuapp.com/graphql"
    WALLET_ADDRESS: str | None = None
    PRIVATE_KEY: str | None = None  # ONLY for live trading

    # Trading Mode
    SIMULATION_MODE: bool = True

    # Risk Management
    MAX_BET_SIZE_USD: float = 100.0
    MAX_DAILY_EXPOSURE: float = 500.0
    MAX_POSITIONS: int = 5
    PORTFOLIO_VALUE: float = 1000.0
    MAX_DRAWDOWN_PCT: float = 0.20  # 20%
    DAILY_LOSS_LIMIT_PCT: float = 0.05  # 5%
    STOP_LOSS_PCT: float = 0.50  # 50%
    TAKE_PROFIT_MULTIPLIER: float = 2.0  # 2x

    # Position sizing
    BET_SIZE_PCT: float = 0.02  # 2% of portfolio per bet
    MAX_EXPOSURE_PER_MARKET_PCT: float = 0.10  # 10%

    # Market filters
    MIN_LIQUIDITY_USD: float = 10000.0  # Minimum market volume
    MAX_DAYS_TO_EXPIRY: int = 7  # Only bet on markets closing within 7 days

    # Email Notifications
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_TO: str | None = None
    EMAIL_FROM: str | None = None

    # Telegram Notifications
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    # Database
    DATABASE_URL: str = "sqlite:///data/pizza_bot.db"

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Strategy
    STRATEGY: Literal["aggressive", "conservative", "hybrid"] = "hybrid"
    PIZZA_SIGNAL_WEIGHT: float = 0.6  # For hybrid strategy
    TRADER_SIGNAL_WEIGHT: float = 0.4  # For hybrid strategy

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure data directory exists for SQLite."""
        if v.startswith("sqlite:///"):
            data_dir = get_project_root() / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Normalize log level to uppercase."""
        return v.upper()

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def is_live_trading(self) -> bool:
        """Check if running in live trading mode."""
        return not self.SIMULATION_MODE and self.WALLET_ADDRESS is not None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings


# For easy import
settings = get_settings()
