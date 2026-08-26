import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


@dataclass
class MT5Config:
    path: str = r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
    login: int = int(os.environ.get("MT5_LOGIN", "0"))
    server: str = os.environ.get("MT5_SERVER", "")
    password: str = os.environ.get("MT5_PASSWORD", "")


@dataclass
class ScoreWeights:
    vwap: float = 0.08
    trend: float = 0.05
    moving_averages: float = 0.05
    momentum: float = 0.08
    volume: float = 0.03
    breakout: float = 0.03
    structure: float = 0.03
    relative_strength: float = 0.05
    adx: float = 0.05
    stochastic: float = 0.03
    bollinger: float = 0.03
    recent_price: float = 0.18
    tick_momentum: float = 0.22
    price_velocity: float = 0.10
    wdo: float = 0.15


@dataclass
class AssetConfig:
    base_price_win: float = 170520.0
    base_price_wdo: float = 5203.50
    tick_size_win: float = 5.0
    tick_size_wdo: float = 0.50
    ema_fast: int = 3
    ema_slow: int = 8
    sma_medium: int = 21
    sma_long: int = 50
    rsi_period: int = 7
    macd_fast: int = 5
    macd_slow: int = 13
    macd_signal: int = 5
    roc_period: int = 5
    update_interval_seconds: int = 1
    candle_timeframe: str = "M1"
    candle_count: int = 100


@dataclass
class MarketConfig:
    score_weights: ScoreWeights = field(default_factory=ScoreWeights)
    asset: AssetConfig = field(default_factory=AssetConfig)
    mt5: MT5Config = field(default_factory=MT5Config)


@dataclass
class AuthConfig:
    secret_key: str = os.environ.get("AUTH_SECRET_KEY", "")
    algorithm: str = "HS256"
    token_expire_minutes: int = int(os.environ.get("AUTH_TOKEN_EXPIRE_MINUTES", "1440"))
    admin_username: str = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password: str = os.environ.get("ADMIN_PASSWORD", "")


settings = MarketConfig()
auth_settings = AuthConfig()
