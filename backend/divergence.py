from __future__ import annotations

from dataclasses import dataclass
from typing import List

from indicators import calc_rsi, calc_macd


@dataclass
class Divergence:
    type: str
    direction: str
    detail: str
    strength: str


def _find_peaks(values: List[float], min_prominence: float = 0) -> List[int]:
    peaks = []
    for i in range(1, len(values) - 1):
        if values[i] > values[i - 1] and values[i] > values[i + 1]:
            if min_prominence == 0 or (values[i] - min(values[i - 1], values[i + 1])) >= min_prominence:
                peaks.append(i)
    return peaks


def _find_troughs(values: List[float], min_prominence: float = 0) -> List[int]:
    troughs = []
    for i in range(1, len(values) - 1):
        if values[i] < values[i - 1] and values[i] < values[i + 1]:
            if min_prominence == 0 or (max(values[i - 1], values[i + 1]) - values[i]) >= min_prominence:
                troughs.append(i)
    return troughs


def detect_divergences(candles: list) -> List[dict]:
    if len(candles) < 30:
        return []

    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]

    rsi_vals = []
    for i in range(len(candles)):
        rsi_vals.append(calc_rsi(candles[:i + 1]))

    macd_vals = []
    for i in range(len(candles)):
        m = calc_macd(candles[:i + 1])
        macd_vals.append(m.get("histogram", 0))

    divergences = []

    price_peaks = _find_peaks(highs)
    rsi_peaks = _find_peaks(rsi_vals)

    if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
        p1, p2 = price_peaks[-2], price_peaks[-1]
        r1, r2 = rsi_peaks[-2], rsi_peaks[-1]

        if highs[p2] > highs[p1] and rsi_vals[r2] < rsi_vals[r1]:
            strength = "FORTE" if (rsi_vals[r1] - rsi_vals[r2]) > 10 else "FRACA"
            divergences.append({
                "type": "BEARISH",
                "direction": "BAIXA",
                "detail": f"Preco fez maxima mais alta ({highs[p2]:.0f} > {highs[p1]:.0f}) mas RSI fez maxima mais baixa ({rsi_vals[r2]:.0f} < {rsi_vals[r1]:.0f})",
                "strength": strength,
            })

    price_troughs = _find_troughs(lows)
    rsi_troughs = _find_troughs(rsi_vals)

    if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
        p1, p2 = price_troughs[-2], price_troughs[-1]
        r1, r2 = rsi_troughs[-2], rsi_troughs[-1]

        if lows[p2] < lows[p1] and rsi_vals[r2] > rsi_vals[r1]:
            strength = "FORTE" if (rsi_vals[r2] - rsi_vals[r1]) > 10 else "FRACA"
            divergences.append({
                "type": "BULLISH",
                "direction": "ALTA",
                "detail": f"Preco fez minima mais baixa ({lows[p2]:.0f} < {lows[p1]:.0f}) mas RSI fez minima mais alta ({rsi_vals[r2]:.0f} > {rsi_vals[r1]:.0f})",
                "strength": strength,
            })

    macd_peaks = _find_peaks(macd_vals)
    if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
        p1, p2 = price_peaks[-2], price_peaks[-1]
        m1, m2 = macd_peaks[-2], macd_peaks[-1]

        if highs[p2] > highs[p1] and macd_vals[m2] < macd_vals[m1]:
            strength = "FORTE" if abs(macd_vals[m1] - macd_vals[m2]) > 5 else "FRACA"
            divergences.append({
                "type": "BEARISH MACD",
                "direction": "BAIXA",
                "detail": f"Preco subindo mas MACD histogram diminuindo ({macd_vals[m2]:.2f} < {macd_vals[m1]:.2f})",
                "strength": strength,
            })

    macd_troughs = _find_troughs(macd_vals)
    if len(price_troughs) >= 2 and len(macd_troughs) >= 2:
        p1, p2 = price_troughs[-2], price_troughs[-1]
        m1, m2 = macd_troughs[-2], macd_troughs[-1]

        if lows[p2] < lows[p1] and macd_vals[m2] > macd_vals[m1]:
            strength = "FORTE" if abs(macd_vals[m2] - macd_vals[m1]) > 5 else "FRACA"
            divergences.append({
                "type": "BULLISH MACD",
                "direction": "ALTA",
                "detail": f"Preco caindo mas MACD histogram aumentando ({macd_vals[m2]:.2f} > {macd_vals[m1]:.2f})",
                "strength": strength,
            })

    return divergences
