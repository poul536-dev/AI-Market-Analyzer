from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from indicators import FullIndicators, calculate_all_indicators
from market_data import Candle


TIMEFRAMES = ["1M", "5M", "15M", "30M", "1H"]
TF_CANDLE_COUNT = {"1M": 390, "5M": 78, "15M": 26, "30M": 13, "1H": 7}


@dataclass
class TimeframeResult:
    timeframe: str
    indicators: FullIndicators
    trend: str
    score: float


def _resample_candles(candles: List[Candle], target_tf: str) -> List[Candle]:
    if not candles:
        return []

    target_count = TF_CANDLE_COUNT.get(target_tf, 26)
    if len(candles) <= target_count:
        return list(candles)

    step = max(1, len(candles) // target_count)
    resampled = []

    for i in range(0, len(candles), step):
        chunk = candles[i:i + step]
        if not chunk:
            continue
        resampled.append(Candle(
            timestamp=chunk[0].timestamp,
            open=chunk[0].open,
            high=max(c.high for c in chunk),
            low=min(c.low for c in chunk),
            close=chunk[-1].close,
            volume=sum(c.volume for c in chunk),
        ))

    return resampled


def _determine_trend(ind: FullIndicators, price: float) -> str:
    ema9 = ind.ema_9
    ema21 = ind.ema_21
    sma50 = ind.sma_50

    if ema9 and ema21 and sma50:
        if ema9 > ema21 > sma50 and price > ema9:
            return "ALTA"
        elif ema9 < ema21 < sma50 and price < ema9:
            return "BAIXA"
    if ema9 and ema21:
        if ema9 > ema21 and price > ema9:
            return "ALTA"
        elif ema9 < ema21 and price < ema9:
            return "BAIXA"
    return "LATERAL"


def _calc_tf_score(ind: FullIndicators, price: float, trend: str) -> float:
    score = 50.0

    if ind.vwap > 0:
        if price > ind.vwap:
            score += 8
        else:
            score -= 8

    if trend == "ALTA":
        score += 10
    elif trend == "BAIXA":
        score -= 10

    if ind.rsi > 60:
        score += 5
    elif ind.rsi < 40:
        score -= 5

    hist = ind.macd.get("histogram", 0)
    if hist > 0:
        score += 5
    elif hist < 0:
        score -= 5

    adx_val = ind.adx.get("adx", 0)
    if adx_val > 25:
        if trend == "ALTA":
            score += 5
        elif trend == "BAIXA":
            score -= 5

    return max(0, min(100, score))


def analyze_multitimeframe(candles: List[Candle]) -> Dict[str, dict]:
    if not candles:
        return {"timeframes": {}, "confluence": "INDISPONIVEL", "score": 50}

    price = candles[-1].close
    results = {}

    for tf in TIMEFRAMES:
        resampled = _resample_candles(candles, tf)
        if not resampled:
            continue

        ind = calculate_all_indicators(resampled)
        trend = _determine_trend(ind, price)
        score = _calc_tf_score(ind, price, trend)

        if score >= 60:
            signal = "COMPRA"
        elif score <= 40:
            signal = "VENDA"
        else:
            signal = "NEUTRO"

        results[tf] = {
            "timeframe": tf,
            "trend": trend,
            "signal": signal,
            "score": round(score, 1),
            "rsi": ind.rsi,
            "macd_hist": ind.macd.get("histogram", 0),
            "adx": ind.adx.get("adx", 0),
        }

    buy_count = sum(1 for r in results.values() if r["signal"] == "COMPRA")
    sell_count = sum(1 for r in results.values() if r["signal"] == "VENDA")
    total = len(results)

    if total == 0:
        confluence = "INDISPONIVEL"
        avg_score = 50
    elif buy_count > total * 0.6:
        confluence = "ALTA"
        avg_score = sum(r["score"] for r in results.values()) / total
    elif sell_count > total * 0.6:
        confluence = "BAIXA"
        avg_score = sum(r["score"] for r in results.values()) / total
    else:
        confluence = "MISTA"
        avg_score = sum(r["score"] for r in results.values()) / total

    return {
        "timeframes": results,
        "confluence": confluence,
        "buy_timeframes": buy_count,
        "sell_timeframes": sell_count,
        "neutral_timeframes": total - buy_count - sell_count,
        "score": round(avg_score, 1),
    }
