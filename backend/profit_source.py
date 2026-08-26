from __future__ import annotations

import logging
import os
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

log = logging.getLogger("profit_source")

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

try:
    from profitdll_wrapper import ProfitClient, Event, Trade, ExchangeCode, DailyCandle

    HAS_PROFITDLL = True
except ImportError:
    HAS_PROFITDLL = False
    log.warning("profitdll-wrapper not installed")

from market_data import Candle


PROFIT_EXCHANGE = "F"

CONTRACT_MAP = {
    "WIN": {"ticker": "WIN", "exchange": PROFIT_EXCHANGE},
    "WDO": {"ticker": "WDO", "exchange": PROFIT_EXCHANGE},
}

TICKER_SUFFIX_MAP = {
    "F": "A",  # Janeiro
    "G": "B",  # Fevereiro
    "H": "C",  # Marco
    "J": "D",  # Abril
    "K": "E",  # Maio
    "M": "F",  # Junho
    "N": "G",  # Julho
    "Q": "H",  # Agosto
    "U": "I",  # Setembro
    "V": "J",  # Outubro
    "X": "K",  # Novembro
    "Z": "L",  # Dezembro
}


def get_current_contract(month_code: str) -> str:
    now = time.localtime()
    year = now.tm_year % 100
    return f"{month_code}{year:02d}"


def get_active_win_ticker() -> str:
    month = time.localtime().tm_mon
    month_codes = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]
    code = month_codes[month - 1]
    return get_current_contract(code)


def get_active_wdo_ticker() -> str:
    return get_active_win_ticker()


class ProfitSource:
    def __init__(self) -> None:
        self._client: Optional[ProfitClient] = None
        self._connected = False
        self._lock = threading.Lock()
        self._trades: Dict[str, List[dict]] = {"WIN": [], "WDO": []}
        self._daily: Dict[str, Optional[dict]] = {"WIN": None, "WDO": None}
        self._last_prices: Dict[str, float] = {"WIN": 0.0, "WDO": 0.0}
        self._candles: Dict[str, List[Candle]] = {"WIN": [], "WDO": []}
        self._tick_count: Dict[str, int] = {"WIN": 0, "WDO": 0}
        self._start_time = time.time()

    def _get_credentials(self) -> Optional[dict]:
        key = os.getenv("PROFIT_ACTIVATION_KEY", "")
        user = os.getenv("PROFIT_USER", "")
        password = os.getenv("PROFIT_PASSWORD", "")

        if not key or key.startswith("sua_"):
            log.warning("ProfitDLL credentials not configured in .env")
            return None
        if not user or user.startswith("seu_"):
            log.warning("ProfitDLL user not configured in .env")
            return None
        if not password or password.startswith("sua_"):
            log.warning("ProfitDLL password not configured in .env")
            return None

        return {"activation_key": key, "user": user, "password": password}

    def connect(self) -> bool:
        if not HAS_PROFITDLL:
            log.error("profitdll-wrapper not installed")
            return False

        creds = self._get_credentials()
        if not creds:
            return False

        try:
            self._client = ProfitClient(
                activation_key=creds["activation_key"],
                user=creds["user"],
                password=creds["password"],
                mode="market_data",
            )

            self._client.on(Event.TRADE)(self._on_trade)
            self._client.on(Event.DAILY)(self._on_daily)

            win_ticker = get_active_win_ticker()
            wdo_ticker = get_active_wdo_ticker()

            log.info("Connecting to ProfitDLL...")
            self._client.connect()

            self._client.subscribe(win_ticker, exchange=PROFIT_EXCHANGE)
            self._client.subscribe(wdo_ticker, exchange=PROFIT_EXCHANGE)

            self._connected = True
            log.info("ProfitDLL connected. Subscribed to %s and %s", win_ticker, wdo_ticker)
            return True

        except Exception as e:
            log.error("Failed to connect ProfitDLL: %s", e)
            self._connected = False
            return False

    def _on_trade(self, trade: Trade) -> None:
        try:
            ticker = trade.asset.ticker if hasattr(trade, "asset") else ""
            price = trade.price if hasattr(trade, "price") else 0

            asset = None
            for key in CONTRACT_MAP:
                if key in ticker.upper():
                    asset = key
                    break

            if asset and price > 0:
                with self._lock:
                    self._last_prices[asset] = price
                    self._tick_count[asset] += 1

                    now = time.time()
                    candles = self._candles[asset]
                    if candles and (now - candles[-1].timestamp) < 60:
                        c = candles[-1]
                        c.high = max(c.high, price)
                        c.low = min(c.low, price)
                        c.close = price
                        c.volume += 1
                    else:
                        candles.append(Candle(
                            timestamp=now,
                            open=price,
                            high=price,
                            low=price,
                            close=price,
                            volume=1,
                        ))
                        if len(candles) > 500:
                            self._candles[asset] = candles[-500:]

        except Exception as e:
            log.error("Error in trade callback: %s", e)

    def _on_daily(self, daily: DailyCandle) -> None:
        try:
            ticker = daily.asset.ticker if hasattr(daily, "asset") else ""

            asset = None
            for key in CONTRACT_MAP:
                if key in ticker.upper():
                    asset = key
                    break

            if asset:
                with self._lock:
                    self._daily[asset] = {
                        "open": daily.open if hasattr(daily, "open") else 0,
                        "high": daily.high if hasattr(daily, "high") else 0,
                        "low": daily.low if hasattr(daily, "low") else 0,
                        "close": daily.close if hasattr(daily, "close") else 0,
                        "volume": daily.volume if hasattr(daily, "volume") else 0,
                    }
        except Exception as e:
            log.error("Error in daily callback: %s", e)

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._connected = False

    def get_asset_data(self, asset: str) -> Optional[dict]:
        asset = asset.upper()
        if asset not in ("WIN", "WDO"):
            return None

        with self._lock:
            price = self._last_prices.get(asset, 0)
            if price <= 0:
                return None

            candles = list(self._candles.get(asset, []))
            daily = self._daily.get(asset)

        if not candles:
            return None

        open_price = candles[0].open
        high = max(c.high for c in candles)
        low = min(c.low for c in candles)
        volume = sum(c.volume for c in candles)
        avg_volume = volume / max(len(candles), 1)

        if daily:
            open_price = daily["open"]
            high = daily["high"]
            low = daily["low"]
            volume = daily["volume"]

        return {
            "price": round(price, 2),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "volume": volume,
            "avg_volume": avg_volume,
            "candles": candles,
            "source": "profitdll",
            "ticker": get_active_win_ticker() if asset == "WIN" else get_active_wdo_ticker(),
            "name": f"ProfitDLL - {asset}",
        }

    def get_all(self) -> dict:
        result = {}
        for asset in ["WIN", "WDO"]:
            data = self.get_asset_data(asset)
            if data:
                result[asset] = data
        result["timestamp"] = time.time()
        return result

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tick_count(self) -> dict:
        return dict(self._tick_count)
