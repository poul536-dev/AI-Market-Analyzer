from __future__ import annotations

from dataclasses import dataclass
from typing import List

from indicators import calc_ema, calc_rsi, calc_macd


@dataclass
class CrossAnalysis:
    correlation: str
    correlation_score: float
    win_trend: str
    wdo_trend: str
    divergence: str
    divergence_detail: str
    spread_pct: float
    spread_direction: str
    wdo_pressure: str
    recommendation: str
    confidence: float
    wdo_influence: float = 0.0
    wdo_score: float = 50.0


def _calc_correlation(win_closes: List[float], wdo_closes: List[float]) -> float:
    min_len = min(len(win_closes), len(wdo_closes))
    if min_len < 5:
        return 0.0

    x = win_closes[-min_len:]
    y = wdo_closes[-min_len:]

    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(a * b for a, b in zip(x, y))
    sum_x2 = sum(a ** 2 for a in x)
    sum_y2 = sum(b ** 2 for b in y)

    num = n * sum_xy - sum_x * sum_y
    den = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5

    if den == 0:
        return 0.0
    return max(-1, min(1, num / den))


def _calc_spread(win_price: float, wdo_price: float) -> float:
    if wdo_price == 0:
        return 0.0
    return round(((win_price / wdo_price) - 1) * 100, 4)


def analyze_cross(win_candles: list, wdo_candles: list) -> dict:
    if not win_candles or not wdo_candles:
        return {
            "correlation": "INDISPONIVEL",
            "correlation_score": 0,
            "win_trend": "INDISPONIVEL",
            "wdo_trend": "INDISPONIVEL",
            "divergence": "NA",
            "divergence_detail": "Sem dados suficientes",
            "spread_pct": 0,
            "spread_direction": "INDISPONIVEL",
            "wdo_pressure": "NEUTRA",
            "recommendation": "AGUARDAR",
            "confidence": 0,
        }

    win_closes = [c.close for c in win_candles]
    wdo_closes = [c.close for c in wdo_candles]
    win_price = win_closes[-1]
    wdo_price = wdo_closes[-1]

    corr = _calc_correlation(win_closes, wdo_closes)

    if corr > 0.7:
        corr_label = "FORTE POSITIVA"
    elif corr > 0.3:
        corr_label = "MODERADA"
    elif corr > -0.3:
        corr_label = "FRACA"
    elif corr > -0.7:
        corr_label = "MODERADA INVERSA"
    else:
        corr_label = "FORTE INVERSA"

    ema9_win = calc_ema(win_candles, 9)
    ema21_win = calc_ema(win_candles, 21)
    ema9_wdo = calc_ema(wdo_candles, 9)
    ema21_wdo = calc_ema(wdo_candles, 21)

    if ema9_win and ema21_win:
        win_trend = "ALTA" if ema9_win > ema21_win else "BAIXA" if ema9_win < ema21_win else "LATERAL"
    else:
        win_trend = "INDISPONIVEL"

    if ema9_wdo and ema21_wdo:
        wdo_trend = "ALTA" if ema9_wdo > ema21_wdo else "BAIXA" if ema9_wdo < ema21_wdo else "LATERAL"
    else:
        wdo_trend = "INDISPONIVEL"

    rsi_win = calc_rsi(win_candles)
    rsi_wdo = calc_rsi(wdo_candles)
    macd_win = calc_macd(win_candles)
    macd_wdo = calc_macd(wdo_candles)

    divergence = "NA"
    divergence_detail = "Indicadores alinhados"

    if win_trend == "ALTA" and wdo_trend == "BAIXA":
        divergence = "DIVERGENCIA FORTE"
        divergence_detail = f"WIN subindo, WDO caindo. RSI WIN={rsi_win:.0f} vs WDO={rsi_wdo:.0f}"
    elif win_trend == "BAIXA" and wdo_trend == "ALTA":
        divergence = "DIVERGENCIA FORTE"
        divergence_detail = f"WIN caindo, WDO subindo. RSI WIN={rsi_win:.0f} vs WDO={rsi_wdo:.0f}"
    elif win_trend != wdo_trend and win_trend != "LATERAL" and wdo_trend != "LATERAL":
        divergence = "DIVERGENCIA FRACA"
        divergence_detail = f"Tendencias opostas: WIN={win_trend}, WDO={wdo_trend}"

    hist_win = macd_win.get("histogram", 0)
    hist_wdo = macd_wdo.get("histogram", 0)
    if hist_win > 0 and hist_wdo < 0 and abs(hist_win) > 5 and abs(hist_wdo) > 5:
        divergence = "DIVERGENCIA MOMENTUM"
        divergence_detail = f"MACD divergente: WIN={hist_win:.2f}, WDO={hist_wdo:.2f}"
    elif hist_win < 0 and hist_wdo > 0 and abs(hist_win) > 5 and abs(hist_wdo) > 5:
        divergence = "DIVERGENCIA MOMENTUM"
        divergence_detail = f"MACD divergente: WIN={hist_win:.2f}, WDO={hist_wdo:.2f}"

    spread = _calc_spread(win_price, wdo_price)
    if spread > 1:
        spread_dir = "EXPANDINDO (WIN forte)"
    elif spread < -1:
        spread_dir = "CONTRAINDO (WDO forte)"
    else:
        spread_dir = "ESTAVEL"

    if rsi_wdo > 65:
        wdo_pressure = "FORTE ALTA (dolar subindo)"
    elif rsi_wdo > 55:
        wdo_pressure = "MODERADA ALTA"
    elif rsi_wdo < 35:
        wdo_pressure = "FORTE BAIXA (dolar caindo)"
    elif rsi_wdo < 45:
        wdo_pressure = "MODERADA BAIXA"
    else:
        wdo_pressure = "NEUTRA"

    confidence = abs(corr) * 30
    if win_trend == wdo_trend and win_trend != "LATERAL":
        confidence += 20
    if rsi_win > 70 or rsi_win < 30:
        confidence += 10
    if rsi_wdo > 70 or rsi_wdo < 30:
        confidence += 10
    confidence = min(100, confidence)

    if divergence == "DIVERGENCIA FORTE":
        if win_trend == "ALTA":
            recommendation = "WIN com vantagem relativa. Priorizar compras em WIN."
        else:
            recommendation = "WDO com vantagem relativa. Considerar vendas em WIN."
    elif divergence == "DIVERGENCIA MOMENTUM":
        recommendation = "Momentum divergente. Atencao para reversao."
    elif wdo_trend == "BAIXA" and win_trend == "ALTA":
        recommendation = "Dolar fraco favorece WIN. Ambiente comprador."
    elif wdo_trend == "ALTA" and win_trend == "BAIXA":
        recommendation = "Dolar forte pressiona WIN. Ambiente vendedor."
    elif corr_label.startswith("FORTE INV"):
        recommendation = "Correlacao inversa forte. Usar um como hedge do outro."
    else:
        recommendation = "Mercado sem sinal claro. Aguardar convergencia."

    wdo_score = 50.0
    if rsi_wdo > 70:
        wdo_score = 80.0
    elif rsi_wdo > 60:
        wdo_score = 65.0
    elif rsi_wdo < 30:
        wdo_score = 20.0
    elif rsi_wdo < 40:
        wdo_score = 35.0

    if hist_wdo > 0 and hist_wdo > abs(hist_win) * 0.5:
        wdo_score = min(90, wdo_score + 10)
    elif hist_wdo < 0 and abs(hist_wdo) > abs(hist_win) * 0.5:
        wdo_score = max(10, wdo_score - 10)

    if wdo_trend == "ALTA":
        wdo_score = min(85, wdo_score + 8)
    elif wdo_trend == "BAIXA":
        wdo_score = max(15, wdo_score - 8)

    wdo_influence = 0.0
    if divergence.startswith("DIVERGENCIA"):
        if wdo_trend == "BAIXA" and win_trend == "ALTA":
            wdo_influence = 8.0
        elif wdo_trend == "ALTA" and win_trend == "BAIXA":
            wdo_influence = -8.0
    elif wdo_pressure.startswith("FORTE ALTA"):
        wdo_influence = -5.0
    elif wdo_pressure.startswith("FORTE BAIXA"):
        wdo_influence = 5.0
    elif wdo_pressure.startswith("MODERADA ALTA"):
        wdo_influence = -3.0
    elif wdo_pressure.startswith("MODERADA BAIXA"):
        wdo_influence = 3.0

    if corr_label.startswith("FORTE POS") and wdo_trend == win_trend:
        if wdo_trend == "ALTA":
            wdo_influence += 4.0
        elif wdo_trend == "BAIXA":
            wdo_influence -= 4.0

    return {
        "correlation": corr_label,
        "correlation_score": round(corr, 4),
        "win_trend": win_trend,
        "wdo_trend": wdo_trend,
        "divergence": divergence,
        "divergence_detail": divergence_detail,
        "spread_pct": spread,
        "spread_direction": spread_dir,
        "wdo_pressure": wdo_pressure,
        "recommendation": recommendation,
        "confidence": round(confidence, 1),
        "rsi_win": rsi_win,
        "rsi_wdo": rsi_wdo,
        "macd_win_hist": hist_win,
        "macd_wdo_hist": hist_wdo,
        "wdo_influence": round(wdo_influence, 1),
        "wdo_score": round(wdo_score, 1),
    }
