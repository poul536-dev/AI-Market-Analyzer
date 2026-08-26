from __future__ import annotations

import logging
import re
import time
from typing import List, Optional

try:
    import MetaTrader5 as mt5

    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False

from market_data import Candle

log = logging.getLogger("mt5_source")

MONTH_CODE = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
              "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}

MT5_TIMEFRAME_MAP = {}
if HAS_MT5:
    MT5_TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "D1": mt5.TIMEFRAME_D1,
    }


def _parse_contract(symbol: str):
    m = re.match(r"^(WIN|WDO)([FGHJKMNQUVXZ])(\d{2})$", symbol.upper())
    if not m:
        return None
    prefix, month_code, year_str = m.groups()
    return prefix, MONTH_CODE.get(month_code, 0), 2000 + int(year_str)


def _find_front_month(asset: str) -> Optional[str]:
    symbols = mt5.symbols_get()
    if not symbols:
        return None

    now = time.localtime()
    current_year = now.tm_year
    current_month = now.tm_mon

    candidates = []
    for s in symbols:
        parsed = _parse_contract(s.name)
        if not parsed:
            continue
        prefix, month, year = parsed
        if prefix != asset.upper():
            continue
        if year < current_year:
            continue
        if year == current_year and month < current_month:
            continue
        candidates.append((year, month, s.name))

    if not candidates:
        return None

    candidates.sort()
    return candidates[0][2]


class MT5Source:
    def __init__(self) -> None:
        self._initialized = False
        self._connected = False
        self._tick_cache = {}
        self._tick_times = {}
        self._symbol_map = {"WIN": None, "WDO": None}

    def initialize(self, path: str = None, login: int = None, password: str = None, server: str = None) -> bool:
        if not HAS_MT5:
            log.warning("MetaTrader5 package not installed")
            return False

        try:
            kwargs = {}
            if path:
                kwargs["path"] = path

            if mt5.initialize(**kwargs):
                self._initialized = True
                self._connected = True
                info = mt5.terminal_info()
                acc = mt5.account_info()
                log.info("MT5 connected: %s | Account: %s | Server: %s",
                         info.name if info else "?",
                         acc.login if acc else "?",
                         acc.server if acc else "?")
                self._resolve_front_months()
                return True
            else:
                error = mt5.last_error()
                log.warning("MT5 initialize without login failed: %s, trying with credentials", error)

            kwargs_login = {}
            if path:
                kwargs_login["path"] = path
            if login:
                kwargs_login["login"] = int(login)
            if password:
                kwargs_login["password"] = password
            if server:
                kwargs_login["server"] = server

            if mt5.initialize(**kwargs_login):
                self._initialized = True
                self._connected = True
                info = mt5.terminal_info()
                acc = mt5.account_info()
                log.info("MT5 connected with login: %s | Account: %s | Server: %s",
                         info.name if info else "?",
                         acc.login if acc else "?",
                         acc.server if acc else "?")
                self._resolve_front_months()
                return True
            else:
                error = mt5.last_error()
                log.error("MT5 initialize with login failed: %s", error)
                return False
        except Exception as e:
            log.error("MT5 init error: %s", e)
            return False

    def _resolve_front_months(self) -> None:
        for asset in ["WIN", "WDO"]:
            sym = _find_front_month(asset)
            if sym:
                mt5.symbol_select(sym, True)
                self._symbol_map[asset] = sym
                log.info("Front month for %s: %s", asset, sym)
            else:
                log.warning("No front month contract found for %s", asset)

    def shutdown(self) -> None:
        if self._initialized:
            try:
                mt5.shutdown()
            except Exception:
                pass
            self._initialized = False
            self._connected = False

    def _resolve_symbol(self, asset: str) -> str:
        asset = asset.upper()
        cached = self._symbol_map.get(asset)
        if cached:
            return cached

        if not self._initialized:
            return ""

        sym = _find_front_month(asset)
        if sym:
            self._symbol_map[asset] = sym
            return sym
        return ""

    def get_tick(self, asset: str) -> Optional[dict]:
        if not self._initialized:
            return None

        symbol = self._resolve_symbol(asset)
        if not symbol:
            return None

        now = time.time()
        cached = self._tick_cache.get(symbol)
        cached_time = self._tick_times.get(symbol, 0)
        if cached and (now - cached_time) < 1.0:
            return cached

        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None

            info = mt5.symbol_info(symbol)
            tick_size = info.point if info else 1.0
            contract_mult = getattr(info, "trade_contract_size", 1.0) if info else 1.0

            spread = (tick.ask - tick.bid) / tick_size if tick_size > 0 else 0

            data = {
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
                "volume": tick.volume,
                "spread": spread,
                "time": tick.time,
                "time_msc": tick.time_msc,
                "flags": tick.flags,
                "tick_size": tick_size,
                "contract_mult": contract_mult,
                "realtime": True,
            }

            self._tick_cache[symbol] = data
            self._tick_times[symbol] = now
            return data
        except Exception as e:
            log.error("MT5 tick error for %s: %s", symbol, e)
            return None

    def get_candles(self, asset: str, timeframe: str = "M5", count: int = 200) -> List[Candle]:
        if not self._initialized:
            return []

        symbol = self._resolve_symbol(asset)
        if not symbol:
            return []

        tf = MT5_TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            return []

        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is None or len(rates) == 0:
                return []

            candles = []
            for r in rates:
                candles.append(Candle(
                    timestamp=r["time"],
                    open=r["open"],
                    high=r["high"],
                    low=r["low"],
                    close=r["close"],
                    volume=r["tick_volume"],
                ))
            return candles
        except Exception as e:
            log.error("MT5 candles error for %s: %s", symbol, e)
            return []

    def get_asset_data(self, asset: str) -> Optional[dict]:
        if not self._initialized:
            return None

        symbol = self._resolve_symbol(asset)
        candles = self.get_candles(asset, "M5", 200)
        if not candles:
            candles = self.get_candles(asset, "D1", 200)
        if not candles:
            return None

        tick = self.get_tick(asset)
        last = candles[-1]
        volumes = [c.volume for c in candles[-60:]]
        avg_vol = sum(volumes) / max(len(volumes), 1)

        price = last.close
        if tick and tick["last"] > 0:
            price = tick["last"]
        elif tick and tick["bid"] > 0:
            price = tick["bid"]

        return {
            "price": round(price, 2),
            "open": round(candles[0].open, 2),
            "high": round(max(c.high for c in candles[-60:]), 2),
            "low": round(min(c.low for c in candles[-60:]), 2),
            "volume": tick["volume"] if tick else last.volume,
            "avg_volume": avg_vol,
            "candles": candles,
            "source": "mt5_realtime",
            "symbol": symbol,
            "bid": tick["bid"] if tick else last.close,
            "ask": tick["ask"] if tick else last.close,
            "spread": tick["spread"] if tick else 0,
            "realtime": True,
        }

    def get_all_data(self) -> dict:
        result = {}
        for asset in ["WIN", "WDO"]:
            data = self.get_asset_data(asset)
            if data:
                result[asset] = data
        result["timestamp"] = time.time()
        return result

    @property
    def is_connected(self) -> bool:
        return self._connected and self._initialized

    def get_connection_info(self) -> dict:
        if not self._initialized:
            return {"connected": False, "error": "MT5 not initialized"}

        try:
            info = mt5.terminal_info()
            account = mt5.account_info()
            return {
                "connected": True,
                "terminal": info.name if info else "Unknown",
                "build": info.build if info else 0,
                "account": account.login if account else 0,
                "server": account.server if account else "",
                "balance": account.balance if account else 0,
                "equity": account.equity if account else 0,
                "margin": account.margin if account else 0,
                "free_margin": account.margin_free if account else 0,
                "symbols": dict(self._symbol_map),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
