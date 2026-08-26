from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from config import settings


@dataclass
class IndicatorResult:
    value: float
    signal: str = "NEUTRO"


def _ema(prices: List[float], period: int) -> List[float]:
    if len(prices) < period:
        return prices[:]
    k = 2.0 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for p in prices[period:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


def _sma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calc_vwap(candles: list) -> float:
    cum_pv = 0.0
    cum_v = 0.0
    day_high = 0.0
    day_low = float("inf")

    for c in candles:
        typical = (c.high + c.low + c.close) / 3.0
        cum_pv += typical * c.volume
        cum_v += c.volume
        day_high = max(day_high, c.high)
        day_low = min(day_low, c.low)

    if cum_v == 0:
        return 0.0
    return round(cum_pv / cum_v, 2)


def calc_ema(candles: list, period: int) -> Optional[float]:
    closes = [c.close for c in candles]
    ema_vals = _ema(closes, period)
    if not ema_vals:
        return None
    return round(ema_vals[-1], 2)


def calc_sma(candles: list, period: int) -> Optional[float]:
    closes = [c.close for c in candles]
    result = _sma(closes, period)
    if result is None:
        return None
    return round(result, 2)


def calc_rsi(candles: list, period: int = 14) -> float:
    closes = [c.close for c in candles]
    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def calc_macd(candles: list) -> dict:
    fast = settings.asset.macd_fast
    slow = settings.asset.macd_slow
    signal = settings.asset.macd_signal
    closes = [c.close for c in candles]

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    offset = slow - fast
    min_len = min(len(ema_fast), len(ema_slow))
    if min_len == 0:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}

    fast_trimmed = ema_fast[-min_len:]
    slow_trimmed = ema_slow[-min_len:]
    macd_line = [f - s for f, s in zip(fast_trimmed, slow_trimmed)]

    if len(macd_line) < signal:
        macd_val = macd_line[-1] if macd_line else 0.0
        return {"macd": round(macd_val, 4), "signal": 0.0, "histogram": round(macd_val, 4)}

    signal_line = _ema(macd_line, signal)
    macd_val = macd_line[-1]
    sig_val = signal_line[-1] if signal_line else 0.0

    return {
        "macd": round(macd_val, 4),
        "signal": round(sig_val, 4),
        "histogram": round(macd_val - sig_val, 4),
    }


def calc_roc(candles: list, period: int = 10) -> float:
    closes = [c.close for c in candles]
    if len(closes) <= period:
        return 0.0
    prev = closes[-period - 1]
    if prev == 0:
        return 0.0
    return round(((closes[-1] - prev) / abs(prev)) * 100, 4)


def calc_support_resistance(candles: list) -> dict:
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]

    day_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    day_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
    open_price = closes[0] if closes else 0.0
    current = closes[-1] if closes else 0.0

    range_size = day_high - day_low
    if range_size == 0:
        range_size = 1.0

    support_1 = round(day_low + range_size * 0.236, 2)
    support_2 = round(day_low + range_size * 0.382, 2)
    resist_1 = round(day_high - range_size * 0.236, 2)
    resist_2 = round(day_high - range_size * 0.382, 2)

    return {
        "day_high": round(day_high, 2),
        "day_low": round(day_low, 2),
        "open": round(open_price, 2),
        "support_1": support_1,
        "support_2": support_2,
        "resist_1": resist_1,
        "resist_2": resist_2,
        "current": round(current, 2),
        "range_size": round(range_size, 2),
    }


def calc_atr(candles: list, period: int = 7) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = candles[i].high
        l = candles[i].low
        pc = candles[i - 1].close
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return round(atr, 2)


def calc_adx(candles: list, period: int = 7) -> dict:
    if len(candles) < period * 2:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0, "trend_strength": "FRACO"}

    plus_dm = []
    minus_dm = []
    trs = []

    for i in range(1, len(candles)):
        h = candles[i].high
        l = candles[i].low
        ph = candles[i - 1].high
        pl = candles[i - 1].low
        pc = candles[i - 1].close

        up = h - ph
        down = pl - l

        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))

    if len(trs) < period:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0, "trend_strength": "FRACO"}

    atr = sum(trs[:period])
    smoothed_plus = sum(plus_dm[:period])
    smoothed_minus = sum(minus_dm[:period])

    dx_values = []
    for i in range(period, len(trs)):
        atr = atr - atr / period + trs[i]
        smoothed_plus = smoothed_plus - smoothed_plus / period + plus_dm[i]
        smoothed_minus = smoothed_minus - smoothed_minus / period + minus_dm[i]

        if atr == 0:
            pdi = 0
            mdi = 0
        else:
            pdi = (smoothed_plus / atr) * 100
            mdi = (smoothed_minus / atr) * 100

        di_sum = pdi + mdi
        if di_sum == 0:
            dx = 0
        else:
            dx = abs(pdi - mdi) / di_sum * 100
        dx_values.append(dx)

    if not dx_values:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0, "trend_strength": "FRACO"}

    adx = sum(dx_values[-period:]) / min(period, len(dx_values))

    if atr == 0:
        final_pdi = 0
        final_mdi = 0
    else:
        final_pdi = (smoothed_plus / atr) * 100
        final_mdi = (smoothed_minus / atr) * 100

    if adx >= 50:
        strength = "MUITO FORTE"
    elif adx >= 25:
        strength = "FORTE"
    elif adx >= 15:
        strength = "MODERADO"
    else:
        strength = "FRACO"

    return {
        "adx": round(adx, 2),
        "plus_di": round(final_pdi, 2),
        "minus_di": round(final_mdi, 2),
        "trend_strength": strength,
    }


def calc_stochastic(candles: list, k_period: int = 7, d_period: int = 3) -> dict:
    if len(candles) < k_period:
        return {"k": 50.0, "d": 50.0, "signal": "NEUTRO"}

    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]

    k_values = []
    for i in range(k_period - 1, len(closes)):
        window_high = max(highs[i - k_period + 1:i + 1])
        window_low = min(lows[i - k_period + 1:i + 1])
        if window_high == window_low:
            k_values.append(50.0)
        else:
            k = ((closes[i] - window_low) / (window_high - window_low)) * 100
            k_values.append(k)

    if not k_values:
        return {"k": 50.0, "d": 50.0, "signal": "NEUTRO"}

    k_val = k_values[-1]
    d_val = sum(k_values[-d_period:]) / min(d_period, len(k_values)) if k_values else 50.0

    if k_val > 80 and d_val > 80:
        signal = "SOBRECOMPRADO"
    elif k_val < 20 and d_val < 20:
        signal = "SOBREVENDIDO"
    elif k_val > d_val and len(k_values) > 1 and k_values[-2] <= sum(k_values[-d_period - 1:-1]) / d_period:
        signal = "COMPRA"
    elif k_val < d_val and len(k_values) > 1 and k_values[-2] >= sum(k_values[-d_period - 1:-1]) / d_period:
        signal = "VENDA"
    else:
        signal = "NEUTRO"

    return {
        "k": round(k_val, 2),
        "d": round(d_val, 2),
        "signal": signal,
    }


def calc_bollinger(candles: list, period: int = 10, std_dev: float = 1.5) -> dict:
    closes = [c.close for c in candles]
    if len(closes) < period:
        return {"upper": 0.0, "middle": 0.0, "lower": 0.0, "bandwidth": 0.0, "position": "MEIO"}

    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = variance ** 0.5

    upper = middle + std_dev * std
    lower = middle - std_dev * std

    if upper == lower:
        bandwidth = 0.0
    else:
        bandwidth = ((upper - lower) / middle) * 100

    current = closes[-1]
    if current >= upper:
        position = "ACIMA superior"
    elif current > middle + (upper - middle) * 0.5:
        position = "FAIXA alta"
    elif current <= lower:
        position = "ABAIXO inferior"
    elif current < middle - (middle - lower) * 0.5:
        position = "FAIXA baixa"
    else:
        position = "MEIO"

    return {
        "upper": round(upper, 2),
        "middle": round(middle, 2),
        "lower": round(lower, 2),
        "bandwidth": round(bandwidth, 4),
        "position": position,
    }


@dataclass
class FullIndicators:
    vwap: float = 0.0
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    rsi: float = 50.0
    macd: dict = None
    roc: float = 0.0
    sr: dict = None
    atr: float = 0.0
    adx: dict = None
    stochastic: dict = None
    bollinger: dict = None

    def __post_init__(self):
        if self.macd is None:
            self.macd = {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
        if self.sr is None:
            self.sr = {}
        if self.adx is None:
            self.adx = {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0, "trend_strength": "FRACO"}
        if self.stochastic is None:
            self.stochastic = {"k": 50.0, "d": 50.0, "signal": "NEUTRO"}
        if self.bollinger is None:
            self.bollinger = {"upper": 0.0, "middle": 0.0, "lower": 0.0, "bandwidth": 0.0, "position": "MEIO"}


def calculate_all_indicators(candles: list) -> FullIndicators:
    period = settings.asset.rsi_period
    return FullIndicators(
        vwap=calc_vwap(candles),
        ema_9=calc_ema(candles, settings.asset.ema_fast),
        ema_21=calc_ema(candles, settings.asset.ema_slow),
        sma_50=calc_sma(candles, settings.asset.sma_medium),
        sma_200=calc_sma(candles, settings.asset.sma_long),
        rsi=calc_rsi(candles, period),
        macd=calc_macd(candles),
        roc=calc_roc(candles, settings.asset.roc_period),
        sr=calc_support_resistance(candles),
        atr=calc_atr(candles),
        adx=calc_adx(candles),
        stochastic=calc_stochastic(candles),
        bollinger=calc_bollinger(candles),
    )
