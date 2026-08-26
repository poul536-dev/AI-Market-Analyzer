from __future__ import annotations

from dataclasses import dataclass

from analysis import AssetAnalysis
from config import settings


@dataclass
class ScoreResult:
    total: int
    label: str
    components: dict
    force: str


def _score_vwap(analysis: AssetAnalysis) -> float:
    pos = analysis.vwap_position
    dist = abs(analysis.vwap_distance_pct)

    if pos == "ACIMA":
        if dist > 0.5:
            return min(100, 50 + dist * 80)
        return min(100, 50 + dist * 50)
    elif pos == "ABAIXO":
        if dist > 0.5:
            return max(0, 50 - dist * 80)
        return max(0, 50 - dist * 50)
    return 50.0


def _score_trend(analysis: AssetAnalysis) -> float:
    trend = analysis.trend
    strength = min(analysis.trend_strength, 100)
    if trend == "ALTA":
        return 50 + strength / 2
    elif trend == "BAIXA":
        return 50 - strength / 2
    return 50.0


def _score_moving_averages(analysis: AssetAnalysis) -> float:
    align = analysis.moving_avg_alignment
    price = analysis.price
    ind = analysis.indicators

    score = 50.0
    if align == "ALTISTA":
        score = 75.0
    elif align == "BAIXISTA":
        score = 25.0

    if ind.ema_9 and price > ind.ema_9:
        score += 8
    elif ind.ema_9 and price < ind.ema_9:
        score -= 8

    if ind.ema_21 and price > ind.ema_21:
        score += 5
    elif ind.ema_21 and price < ind.ema_21:
        score -= 5

    return max(0, min(100, score))


def _score_momentum(analysis: AssetAnalysis) -> float:
    return analysis.momentum_value


def _score_volume(analysis: AssetAnalysis) -> float:
    ratio = analysis.volume_ratio
    trend = analysis.trend

    if ratio > 1.5 and trend == "ALTA":
        return 80.0
    elif ratio > 1.5 and trend == "BAIXA":
        return 20.0
    elif ratio > 1.2:
        return 65.0 if trend == "ALTA" else 35.0
    elif ratio < 0.7:
        return 40.0
    return 50.0


def _score_breakout(analysis: AssetAnalysis) -> float:
    sr = analysis.indicators.sr
    price = analysis.price
    day_high = sr.get("day_high", 0)
    day_low = sr.get("day_low", 0)
    resist_1 = sr.get("resist_1", 0)
    support_1 = sr.get("support_1", 0)

    score = 50.0
    if day_high > 0 and price >= day_high * 0.998:
        score = 85.0
    elif resist_1 > 0 and price > resist_1:
        score = 70.0

    if day_low > 0 and price <= day_low * 1.002:
        score = 15.0
    elif support_1 > 0 and price < support_1:
        score = 30.0

    return max(0, min(100, score))


def _score_structure(analysis: AssetAnalysis) -> float:
    trend = analysis.trend
    momentum = analysis.momentum
    vwap = analysis.vwap_position

    score = 50.0
    if trend == "ALTA":
        score += 15
    elif trend == "BAIXA":
        score -= 15

    if momentum in ("FORTE", "MODERADO"):
        score += 10
    elif momentum in ("FRACO", "MUITO FRACO"):
        score -= 10

    if vwap == "ACIMA":
        score += 8
    elif vwap == "ABAIXO":
        score -= 8

    return max(0, min(100, score))


def _score_relative_strength(analysis: AssetAnalysis) -> float:
    rsi = analysis.indicators.rsi
    roc = analysis.indicators.roc

    score = 50.0
    if rsi > 60:
        score += (rsi - 60) * 1.25
    elif rsi < 40:
        score -= (40 - rsi) * 1.25

    if roc > 0:
        score += min(roc * 10, 15)
    elif roc < 0:
        score += max(roc * 10, -15)

    return max(0, min(100, score))


def _score_adx(analysis: AssetAnalysis) -> float:
    adx = analysis.indicators.adx
    adx_val = adx.get("adx", 0)
    plus_di = adx.get("plus_di", 0)
    minus_di = adx.get("minus_di", 0)
    trend = analysis.trend

    if adx_val < 15:
        if plus_di > minus_di:
            return 60.0
        elif minus_di > plus_di:
            return 40.0
        return 50.0

    if trend == "ALTA":
        if plus_di > minus_di and adx_val > 25:
            return min(85, 50 + adx_val)
        elif minus_di > plus_di:
            return max(15, 50 - adx_val * 1.5)
    elif trend == "BAIXA":
        if minus_di > plus_di and adx_val > 25:
            return max(15, 50 - adx_val)
        elif plus_di > minus_di:
            return min(85, 50 + adx_val * 1.5)

    if plus_di > minus_di:
        return min(70, 50 + adx_val * 0.8)
    elif minus_di > plus_di:
        return max(30, 50 - adx_val * 0.8)

    return 50.0


def _score_stochastic(analysis: AssetAnalysis) -> float:
    stoch = analysis.indicators.stochastic
    k = stoch.get("k", 50)
    d = stoch.get("d", 50)
    trend = analysis.trend

    score = 50.0
    if k > 80 and d > 80:
        score = 30.0 if trend != "ALTA" else 55.0
    elif k < 20 and d < 20:
        score = 70.0 if trend != "BAIXA" else 45.0
    elif k > d:
        score = 60.0 if trend == "ALTA" else 45.0
    elif k < d:
        score = 40.0 if trend == "BAIXA" else 55.0

    return max(0, min(100, score))


def _score_bollinger(analysis: AssetAnalysis) -> float:
    boll = analysis.indicators.bollinger
    position = boll.get("position", "MEIO")

    if position == "ACIMA superior":
        return 35.0
    elif position == "ABAIXO inferior":
        return 65.0
    elif position == "FAIXA alta":
        return 55.0
    elif position == "FAIXA baixa":
        return 45.0
    return 50.0


def _score_recent_price(analysis: AssetAnalysis) -> float:
    rc = analysis.recent_change_pct
    if rc < -0.5:
        return 10.0
    elif rc < -0.3:
        return 20.0
    elif rc < -0.1:
        return 35.0
    elif rc > 0.5:
        return 90.0
    elif rc > 0.3:
        return 80.0
    elif rc > 0.1:
        return 65.0
    return 50.0


def _score_tick_momentum(analysis: AssetAnalysis) -> float:
    tm = analysis.tick_momentum
    if tm >= 80:
        return 85.0
    elif tm >= 70:
        return 70.0
    elif tm >= 60:
        return 60.0
    elif tm <= 20:
        return 15.0
    elif tm <= 30:
        return 30.0
    elif tm <= 40:
        return 40.0
    return 50.0


def _score_price_velocity(analysis: AssetAnalysis) -> float:
    v = analysis.price_velocity
    tick = 5.0 if "WIN" in analysis.asset.upper() else 0.50
    if v > tick * 3:
        return 85.0
    elif v > tick * 2:
        return 75.0
    elif v > tick:
        return 65.0
    elif v < -tick * 3:
        return 15.0
    elif v < -tick * 2:
        return 25.0
    elif v < -tick:
        return 35.0
    return 50.0


def calculate_score(analysis: AssetAnalysis) -> ScoreResult:
    w = settings.score_weights

    components = {
        "vwap": round(_score_vwap(analysis), 1),
        "trend": round(_score_trend(analysis), 1),
        "moving_averages": round(_score_moving_averages(analysis), 1),
        "momentum": round(_score_momentum(analysis), 1),
        "volume": round(_score_volume(analysis), 1),
        "breakout": round(_score_breakout(analysis), 1),
        "structure": round(_score_structure(analysis), 1),
        "relative_strength": round(_score_relative_strength(analysis), 1),
        "adx": round(_score_adx(analysis), 1),
        "stochastic": round(_score_stochastic(analysis), 1),
        "bollinger": round(_score_bollinger(analysis), 1),
        "recent_price": round(_score_recent_price(analysis), 1),
        "tick_momentum": round(_score_tick_momentum(analysis), 1),
        "price_velocity": round(_score_price_velocity(analysis), 1),
    }

    total_raw = (
        components["vwap"] * w.vwap
        + components["trend"] * w.trend
        + components["moving_averages"] * w.moving_averages
        + components["momentum"] * w.momentum
        + components["volume"] * w.volume
        + components["breakout"] * w.breakout
        + components["structure"] * w.structure
        + components["relative_strength"] * w.relative_strength
        + components["adx"] * w.adx
        + components["stochastic"] * w.stochastic
        + components["bollinger"] * w.bollinger
        + components["recent_price"] * getattr(w, "recent_price", 0.18)
        + components["tick_momentum"] * getattr(w, "tick_momentum", 0.22)
        + components["price_velocity"] * getattr(w, "price_velocity", 0.10)
    )

    total = max(0, min(100, round(total_raw)))

    if total <= 20:
        label = "VENDA MUITO FORTE"
    elif total <= 38:
        label = "VENDA"
    elif total <= 47:
        label = "NEUTRO"
    elif total <= 62:
        label = "COMPRA"
    else:
        label = "COMPRA MUITO FORTE"

    if total >= 52:
        force = "COMPRADORA"
    elif total <= 48:
        force = "VEDORA"
    else:
        force = "NEUTRA"

    return ScoreResult(total=total, label=label, components=components, force=force)


def calculate_probability(analysis: AssetAnalysis, score: ScoreResult) -> dict:
    base = score.total
    trend_bonus = 0
    if analysis.trend == "ALTA":
        trend_bonus = 5
    elif analysis.trend == "BAIXA":
        trend_bonus = -5

    vwap_bonus = 0
    if analysis.vwap_position == "ACIMA":
        vwap_bonus = 3
    elif analysis.vwap_position == "ABAIXO":
        vwap_bonus = -3

    momentum_bonus = 0
    if analysis.momentum in ("FORTE",):
        momentum_bonus = 4
    elif analysis.momentum in ("FRACO", "MUITO FRACO"):
        momentum_bonus = -4

    prob_up = base + trend_bonus + vwap_bonus + momentum_bonus
    prob_up = max(5, min(95, prob_up))
    prob_down = 100 - prob_up

    return {
        "probability_up": prob_up,
        "probability_down": prob_down,
    }
