from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

try:
    import yfinance as yf
    import pandas as pd

    HAS_YAHOO = True
except ImportError:
    HAS_YAHOO = False

from config import settings

log = logging.getLogger("market_data")


@dataclass
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


YAHOO_TICKERS = {
    "IBOV": "^BVSP",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
    "VIX": "^VIX",
    "OIL": "CL=F",
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    "USDBRL": "USDBRL=X",
}


class YahooFinanceSource:
    def __init__(self) -> None:
        self._last_fetch = 0.0
        self._cache: dict = {}
        self._cache_tickers: dict = {}
        self._fetch_interval = 60.0

    def _fetch_ticker(self, symbol: str, period: str = "5d", interval: str = "1d") -> Optional[pd.DataFrame]:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period=period, interval=interval)
            if hist.empty:
                log.warning("Empty data for %s", symbol)
                return None
            return hist
        except Exception as e:
            log.error("Error fetching %s: %s", symbol, e)
            return None

    def _hist_to_candles(self, df: pd.DataFrame) -> List[Candle]:
        candles = []
        for idx, row in df.iterrows():
            ts = idx.timestamp() if hasattr(idx, "timestamp") else time.time()
            candles.append(Candle(
                timestamp=ts,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0)),
            ))
        return candles

    def _build_asset_from_ticker(self, symbol: str, name: str) -> Optional[dict]:
        now = time.time()
        cached = self._cache_tickers.get(symbol)
        if cached and (now - cached["time"]) < self._fetch_interval:
            return cached["data"]

        hist = self._fetch_ticker(symbol, period="60d", interval="1d")
        if hist is None or hist.empty:
            return None

        candles = self._hist_to_candles(hist)
        if not candles:
            return None

        last = candles[-1]
        open_price = candles[0].close if len(candles) > 1 else last.open
        volumes = [c.volume for c in candles[-60:]]
        avg_vol = sum(volumes) / max(len(volumes), 1)

        data = {
            "price": round(last.close, 2),
            "open": round(open_price, 2),
            "high": round(max(c.high for c in candles[-60:]), 2),
            "low": round(min(c.low for c in candles[-60:]), 2),
            "volume": last.volume,
            "avg_volume": avg_vol,
            "candles": candles,
            "source": "yahoo",
            "ticker": symbol,
            "name": name,
        }

        self._cache_tickers[symbol] = {"data": data, "time": now}
        return data

    def get_win_data(self) -> Optional[dict]:
        return self._build_asset_from_ticker("^BVSP", "IBOVESPA (proxy WIN)")

    def get_wdo_data(self) -> Optional[dict]:
        return self._build_asset_from_ticker("USDBRL=X", "USD/BRL (proxy WDO)")

    def get_global_data(self) -> dict:
        now = time.time()
        if now - self._last_fetch < self._fetch_interval:
            return self._cache

        self._last_fetch = now
        result = {}

        for name, ticker in YAHOO_TICKERS.items():
            data = self._build_asset_from_ticker(ticker, name)
            if data:
                result[name] = data

        return result

    def get_ticker_info(self, symbol: str) -> dict:
        try:
            t = yf.Ticker(symbol)
            info = t.info
            return {
                "name": info.get("shortName") or info.get("longName", symbol),
                "currency": info.get("currency", ""),
                "exchange": info.get("exchange", ""),
                "market": info.get("market", ""),
            }
        except Exception:
            return {"name": symbol, "currency": "", "exchange": "", "market": ""}


class SimulatedDataSource:
    def __init__(self) -> None:
        self._last_update = 0.0
        self._cache: dict = {}
        self._candles_win: List[Candle] = []
        self._candles_wdo: List[Candle] = []
        self._base_win = settings.asset.base_price_win
        self._base_wdo = settings.asset.base_price_wdo
        self._init_history()

    def _init_history(self) -> None:
        now = time.time()
        price_win = self._base_win - 150.0
        price_wdo = self._base_wdo - 15.0

        for i in range(200):
            ts = now - (200 - i) * 60
            delta_win = random.uniform(-40, 45)
            delta_wdo = random.uniform(-5, 6)
            price_win = max(self._base_win - 500, min(self._base_win + 500, price_win + delta_win))
            price_wdo = max(self._base_wdo - 50, min(self._base_wdo + 50, price_wdo + delta_wdo))
            vol = random.randint(800, 5000)
            o = price_win + random.uniform(-10, 10)
            h = max(price_win, o) + random.uniform(0, 25)
            l = min(price_win, o) - random.uniform(0, 25)
            self._candles_win.append(Candle(ts, round(o, 0), round(h, 0), round(l, 0), round(price_win, 0), vol))

            vol_w = random.randint(400, 3000)
            o_w = price_wdo + random.uniform(-2, 2)
            h_w = max(price_wdo, o_w) + random.uniform(0, 4)
            l_w = min(price_wdo, o_w) - random.uniform(0, 4)
            self._candles_wdo.append(Candle(ts, round(o_w, 2), round(h_w, 2), round(l_w, 2), round(price_wdo, 2), vol_w))

    def _tick(self) -> dict:
        now = time.time()
        if now - self._last_update < settings.asset.update_interval_seconds:
            return self._cache

        self._last_update = now
        last_win = self._candles_win[-1]
        last_wdo = self._candles_wdo[-1]

        delta_win = random.uniform(-35, 38)
        delta_wdo = random.uniform(-4, 5)

        new_close_win = round(max(self._base_win - 500, min(self._base_win + 500, last_win.close + delta_win)), 0)
        new_close_wdo = round(max(self._base_wdo - 50, min(self._base_wdo + 50, last_wdo.close + delta_wdo)), 2)

        vol_win = random.randint(1000, 8000)
        vol_wdo = random.randint(500, 4000)

        ts = now
        o_win = last_win.close
        h_win = max(o_win, new_close_win) + random.uniform(0, 20)
        l_win = min(o_win, new_close_win) - random.uniform(0, 20)
        self._candles_win.append(Candle(ts, o_win, round(h_win, 0), round(l_win, 0), new_close_win, vol_win))
        if len(self._candles_win) > 500:
            self._candles_win = self._candles_win[-500:]

        o_wdo = last_wdo.close
        h_wdo = max(o_wdo, new_close_wdo) + random.uniform(0, 3)
        l_wdo = min(o_wdo, new_close_wdo) - random.uniform(0, 3)
        self._candles_wdo.append(Candle(ts, o_wdo, round(h_wdo, 2), round(l_wdo, 2), new_close_wdo, vol_wdo))
        if len(self._candles_wdo) > 500:
            self._candles_wdo = self._candles_wdo[-500:]

        open_win = self._candles_win[0].open
        open_wdo = self._candles_wdo[0].open

        self._cache = {
            "WIN": {
                "price": new_close_win,
                "open": open_win,
                "high": max(c.high for c in self._candles_win[-60:]),
                "low": min(c.low for c in self._candles_win[-60:]),
                "volume": vol_win,
                "avg_volume": sum(c.volume for c in self._candles_win[-60:]) / max(len(self._candles_win[-60:]), 1),
                "candles": self._candles_win,
                "source": "simulated",
            },
            "WDO": {
                "price": new_close_wdo,
                "open": open_wdo,
                "high": max(c.high for c in self._candles_wdo[-60:]),
                "low": min(c.low for c in self._candles_wdo[-60:]),
                "volume": vol_wdo,
                "avg_volume": sum(c.volume for c in self._candles_wdo[-60:]) / max(len(self._candles_wdo[-60:]), 1),
                "candles": self._candles_wdo,
                "source": "simulated",
            },
            "timestamp": ts,
        }
        return self._cache

    def get_all(self) -> dict:
        return self._tick()


class MarketDataService:
    def __init__(self) -> None:
        self._simulated = SimulatedDataSource()
        self._yahoo: Optional[YahooFinanceSource] = None
        self._brapi = None
        self._mt5 = None
        self._use_yahoo = HAS_YAHOO
        self._use_brapi = False
        self._use_mt5 = False

        try:
            from mt5_source import MT5Source
            self._mt5 = MT5Source()
            mt5_cfg = settings.mt5
            if self._mt5.initialize(
                path=mt5_cfg.path,
                login=mt5_cfg.login,
                password=mt5_cfg.password,
                server=mt5_cfg.server,
            ):
                self._use_mt5 = True
                log.info("MetaTrader5 connected — real-time data available")
            else:
                log.info("MetaTrader5 not available, using fallback")
                self._mt5 = None
        except Exception as e:
            log.info("MetaTrader5 not available: %s", e)

        if not self._use_mt5:
            try:
                from brapi_source import BrapiSource
                self._brapi = BrapiSource()
                test_win = self._brapi.get_asset_data("WIN")
                test_wdo = self._brapi.get_asset_data("WDO")
                if (test_win and test_win.get("price", 0) > 0) or (test_wdo and test_wdo.get("price", 0) > 0):
                    self._use_brapi = True
                    log.info("brapi.dev connected — WIN: %s, WDO: %s",
                             test_win.get("price") if test_win else "N/A",
                             test_wdo.get("price") if test_wdo else "N/A")
                else:
                    log.info("brapi.dev not returning data, using fallback")
                    self._brapi = None
            except Exception as e:
                log.info("brapi.dev not available: %s", e)

        if HAS_YAHOO:
            try:
                self._yahoo = YahooFinanceSource()
                log.info("Yahoo Finance source initialized")
            except Exception as e:
                log.warning("Failed to init Yahoo Finance: %s", e)
                self._use_yahoo = False
        else:
            log.warning("yfinance not installed")

    def get_asset_data(self, asset: str) -> dict:
        asset = asset.upper()

        if self._use_mt5 and self._mt5:
            data = self._mt5.get_asset_data(asset)
            if data:
                return data

        if self._use_brapi and self._brapi:
            data = self._brapi.get_asset_data(asset)
            if data:
                return data

        if self._use_yahoo and self._yahoo:
            data = None
            if asset == "WIN":
                data = self._yahoo.get_win_data()
            elif asset == "WDO":
                data = self._yahoo.get_wdo_data()
            if data:
                return data

        sim = self._simulated.get_all()
        return sim.get(asset, {})

    def get_full_data(self) -> dict:
        result = {}

        if self._use_mt5 and self._mt5:
            mt5_data = self._mt5.get_all_data()
            for asset in ["WIN", "WDO"]:
                if asset in mt5_data:
                    result[asset] = mt5_data[asset]
            result["timestamp"] = mt5_data.get("timestamp", time.time())

        if not self._use_mt5 and self._use_brapi and self._brapi:
            brapi_data = self._brapi.get_all()
            for asset in ["WIN", "WDO"]:
                if asset in brapi_data:
                    result[asset] = brapi_data[asset]
            result["timestamp"] = brapi_data.get("timestamp", time.time())

        if self._use_yahoo and self._yahoo:
            if "WIN" not in result:
                win_data = self._yahoo.get_win_data()
                if win_data:
                    result["WIN"] = win_data
            if "WDO" not in result:
                wdo_data = self._yahoo.get_wdo_data()
                if wdo_data:
                    result["WDO"] = wdo_data

        if "timestamp" not in result:
            result["timestamp"] = time.time()

        if "WIN" not in result:
            sim = self._simulated.get_all()
            result["WIN"] = sim.get("WIN", {})
        if "WDO" not in result:
            sim = self._simulated.get_all()
            result["WDO"] = sim.get("WDO", {})

        return result

    def get_global_markets(self) -> dict:
        if self._use_yahoo and self._yahoo:
            return self._yahoo.get_global_data()
        return {}

    def get_ticker_info(self, symbol: str) -> dict:
        if self._use_yahoo and self._yahoo:
            return self._yahoo.get_ticker_info(symbol)
        return {}

    def get_mt5_connection(self) -> dict:
        if self._mt5:
            return self._mt5.get_connection_info()
        return {
            "connected": False,
            "available": False,
            "error": "MT5 not available (Linux/cloud server)",
            "fallback_source": self.data_source,
        }

    @property
    def data_source(self) -> str:
        if self._use_mt5 and self._mt5:
            return "mt5_realtime"
        if self._use_brapi and self._brapi:
            return "brapi_dev"
        if self._use_yahoo and self._yahoo:
            return "yahoo_finance"
        return "simulated"
