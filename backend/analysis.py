from __future__ import annotations

from dataclasses import dataclass

from indicators import FullIndicators, calculate_all_indicators
from market_data import MarketDataService


@dataclass
class AssetAnalysis:
    asset: str
    price: float
    open_price: float
    high: float
    low: float
    variation: float
    variation_pct: float
    volume: float
    avg_volume: float
    volume_ratio: float
    indicators: FullIndicators
    trend: str
    trend_strength: float
    vwap_position: str
    vwap_distance_pct: float
    moving_avg_alignment: str
    momentum: str
    momentum_value: float
    rsi_zone: str
    support_strength: str
    resist_strength: str


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


def _determine_moving_alignment(ind: FullIndicators) -> str:
    vals = [v for v in [ind.ema_9, ind.ema_21, ind.sma_50, ind.sma_200] if v is not None]
    if len(vals) < 3:
        return "INDEFINIDO"
    if vals[0] > vals[1] > vals[2]:
        return "ALTISTA"
    elif vals[0] < vals[1] < vals[2]:
        return "BAIXISTA"
    return "MISTO"


def _determine_momentum(rsi: float, macd: dict, roc: float) -> tuple:
    score = 50.0
    if rsi > 70:
        score += 20
    elif rsi > 60:
        score += 10
    elif rsi < 30:
        score -= 20
    elif rsi < 40:
        score -= 10

    hist = macd.get("histogram", 0)
    if hist > 0:
        score += 15
    elif hist < 0:
        score -= 15

    if roc > 0.1:
        score += 10
    elif roc < -0.1:
        score -= 10

    score = max(0, min(100, score))

    if score >= 65:
        label = "FORTE"
    elif score >= 55:
        label = "MODERADO"
    elif score >= 45:
        label = "NEUTRO"
    elif score >= 35:
        label = "FRACO"
    else:
        label = "MUITO FRACO"

    return label, round(score, 2)


def analyze_asset(asset: str, data: dict, indicators: FullIndicators) -> AssetAnalysis:
    price = data["price"]
    open_price = data["open"]
    high = data["high"]
    low = data["low"]
    volume = data["volume"]
    avg_volume = data["avg_volume"]

    variation = round(price - open_price, 2)
    variation_pct = round((variation / abs(open_price)) * 100, 4) if open_price != 0 else 0.0
    volume_ratio = round(volume / avg_volume, 2) if avg_volume > 0 else 1.0

    trend = _determine_trend(indicators, price)
    trend_strength = round(abs(variation_pct) * 10, 2)

    if indicators.vwap > 0:
        vwap_dist = ((price - indicators.vwap) / indicators.vwap) * 100
        vwap_distance_pct = round(vwap_dist, 4)
        if vwap_dist > 0.05:
            vwap_pos = "ACIMA"
        elif vwap_dist < -0.05:
            vwap_pos = "ABAIXO"
        else:
            vwap_pos = "NEAR VWAP"
    else:
        vwap_distance_pct = 0.0
        vwap_pos = "INDISPONIVEL"

    moving_alignment = _determine_moving_alignment(indicators)
    momentum_label, momentum_score = _determine_momentum(indicators.rsi, indicators.macd, indicators.roc)

    rsi_zone = "SOBRECOMPRADO" if indicators.rsi > 70 else "SOBREVENDIDO" if indicators.rsi < 30 else "NEUTRO"

    sr = indicators.sr
    support_strength = "FORTE" if sr.get("support_1", 0) > 0 else "FRACO"
    resist_strength = "FORTE" if sr.get("resist_1", 0) > 0 else "FRACO"

    return AssetAnalysis(
        asset=asset,
        price=price,
        open_price=open_price,
        high=high,
        low=low,
        variation=variation,
        variation_pct=variation_pct,
        volume=volume,
        avg_volume=avg_volume,
        volume_ratio=volume_ratio,
        indicators=indicators,
        trend=trend,
        trend_strength=min(trend_strength, 100.0),
        vwap_position=vwap_pos,
        vwap_distance_pct=vwap_distance_pct,
        moving_avg_alignment=moving_alignment,
        momentum=momentum_label,
        momentum_value=momentum_score,
        rsi_zone=rsi_zone,
        support_strength=support_strength,
        resist_strength=resist_strength,
    )


class AnalysisEngine:
    def __init__(self, market_service: MarketDataService) -> None:
        self._market = market_service

    def analyze(self, asset: str) -> AssetAnalysis:
        data = self._market.get_asset_data(asset)
        if not data:
            raise ValueError(f"Asset {asset} not found")
        candles = data["candles"]
        ind = calculate_all_indicators(candles)
        return analyze_asset(asset, data, ind)

    def analyze_all(self) -> dict:
        full = self._market.get_full_data()
        results = {}
        for asset in ["WIN", "WDO"]:
            data = full.get(asset, {})
            if data:
                candles = data["candles"]
                ind = calculate_all_indicators(candles)
                results[asset] = analyze_asset(asset, data, ind)
        return results
