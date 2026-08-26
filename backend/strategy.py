from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class SignalType(str, Enum):
    BUY = "COMPRA"
    SELL = "VENDA"
    NEUTRAL = "NEUTRO"


class TrendFilter(str, Enum):
    ANY = "QUALQUER"
    UP_ONLY = "SOMENTE ALTA"
    DOWN_ONLY = "SOMENTE BAIXA"
    LATERAL_ONLY = "SOMENTE LATERAL"


class ConfirmationType(str, Enum):
    NONE = "NENHUM"
    ADX = "ADX"
    RSI = "RSI"
    VOLUME = "VOLUME"
    VWAP = "VWAP"
    STOCHASTIC = "ESTOCASTICO"
    BOLLINGER = "BOLLINGER"
    MULTI = "MULTIPLO"


@dataclass
class StrategyConfig:
    name: str = "Default"
    asset: str = "WIN"
    signal_type: SignalType = SignalType.BUY
    trend_filter: TrendFilter = TrendFilter.ANY
    confirmations: List[ConfirmationType] = field(default_factory=lambda: [ConfirmationType.ADX, ConfirmationType.RSI])
    min_score: float = 60.0
    min_adx: float = 20.0
    rsi_min: float = 40.0
    rsi_max: float = 60.0
    volume_min_ratio: float = 1.0
    vwap_filter: str = "QUALQUER"
    stochastic_filter: str = "QUALQUER"
    bollinger_filter: str = "QUALQUER"
    min_correlation: float = 0.0
    max_spread_pct: float = 5.0
    tp_ticks: int = 10
    sl_ticks: int = 5
    max_daily_loss: float = 500.0
    max_daily_trades: int = 5


@dataclass
class StrategyResult:
    signal: SignalType
    confidence: float
    score: float
    entry_price: float
    tp_price: float
    sl_price: float
    risk_reward: float
    filters_passed: List[str]
    filters_failed: List[str]
    reason: str


class StrategyEngine:
    def __init__(self) -> None:
        self._strategies: dict[str, StrategyConfig] = {}
        self._active_strategy: Optional[str] = None
        self._load_defaults()

    def _load_defaults(self) -> None:
        self._strategies["COMPRA WIN CONSERVADORA"] = StrategyConfig(
            name="COMPRA WIN CONSERVADORA",
            asset="WIN",
            signal_type=SignalType.BUY,
            trend_filter=TrendFilter.UP_ONLY,
            confirmations=[ConfirmationType.ADX, ConfirmationType.RSI, ConfirmationType.VOLUME],
            min_score=70.0,
            min_adx=25.0,
            rsi_min=45.0,
            rsi_max=65.0,
            volume_min_ratio=1.2,
            tp_ticks=15,
            sl_ticks=8,
        )
        self._strategies["VENDA WIN CONSERVADORA"] = StrategyConfig(
            name="VENDA WIN CONSERVADORA",
            asset="WIN",
            signal_type=SignalType.SELL,
            trend_filter=TrendFilter.DOWN_ONLY,
            confirmations=[ConfirmationType.ADX, ConfirmationType.RSI, ConfirmationType.VOLUME],
            min_score=30.0,
            min_adx=25.0,
            rsi_min=35.0,
            rsi_max=55.0,
            volume_min_ratio=1.2,
            tp_ticks=15,
            sl_ticks=8,
        )
        self._strategies["COMPRA WDO CONSERVADORA"] = StrategyConfig(
            name="COMPRA WDO CONSERVADORA",
            asset="WDO",
            signal_type=SignalType.BUY,
            trend_filter=TrendFilter.UP_ONLY,
            confirmations=[ConfirmationType.ADX, ConfirmationType.RSI],
            min_score=70.0,
            min_adx=20.0,
            rsi_min=40.0,
            rsi_max=65.0,
            tp_ticks=20,
            sl_ticks=10,
        )
        self._strategies["VENDA WDO CONSERVADORA"] = StrategyConfig(
            name="VENDA WDO CONSERVADORA",
            asset="WDO",
            signal_type=SignalType.SELL,
            trend_filter=TrendFilter.DOWN_ONLY,
            confirmations=[ConfirmationType.ADX, ConfirmationType.RSI],
            min_score=30.0,
            min_adx=20.0,
            rsi_min=35.0,
            rsi_max=60.0,
            tp_ticks=20,
            sl_ticks=10,
        )

    def get_strategies(self) -> dict:
        return {k: {
            "name": v.name,
            "asset": v.asset,
            "signal_type": v.signal_type.value,
            "trend_filter": v.trend_filter.value,
            "min_score": v.min_score,
            "tp_ticks": v.tp_ticks,
            "sl_ticks": v.sl_ticks,
        } for k, v in self._strategies.items()}

    def evaluate(self, strategy_name: str, analysis_data: dict, cross_data: dict = None) -> dict:
        if strategy_name not in self._strategies:
            return {"error": f"Estrategia '{strategy_name}' nao encontrada"}

        config = self._strategies[strategy_name]
        filters_passed = []
        filters_failed = []

        score = analysis_data.get("score", 50)
        trend = analysis_data.get("tendencia", "LATERAL")
        adx = analysis_data.get("adx", {})
        rsi = analysis_data.get("rsi", 50)
        volume_ratio = analysis_data.get("volume_ratio", 1.0)
        vwap_pos = analysis_data.get("vwap_position", "INDISPONIVEL")
        stoch = analysis_data.get("stochastic", {})
        boll = analysis_data.get("bollinger", {})
        price = analysis_data.get("price", 0)

        adx_val = adx.get("adx", 0) if isinstance(adx, dict) else 0
        stoch_k = stoch.get("k", 50) if isinstance(stoch, dict) else 50
        boll_pos = boll.get("position", "MEIO") if isinstance(boll, dict) else "MEIO"

        if config.signal_type == SignalType.BUY:
            if score >= config.min_score:
                filters_passed.append(f"Score {score:.0f} >= {config.min_score}")
            else:
                filters_failed.append(f"Score {score:.0f} < {config.min_score}")

            if config.trend_filter == TrendFilter.UP_ONLY and trend == "ALTA":
                filters_passed.append(f"Tendencia {trend} == ALTA")
            elif config.trend_filter == TrendFilter.UP_ONLY:
                filters_failed.append(f"Tendencia {trend} != ALTA")
            elif config.trend_filter == TrendFilter.DOWN_ONLY and trend == "BAIXA":
                filters_passed.append(f"Tendencia {trend} == BAIXA")
            elif config.trend_filter == TrendFilter.DOWN_ONLY:
                filters_failed.append(f"Tendencia {trend} != BAIXA")
            elif config.trend_filter == TrendFilter.LATERAL_ONLY and trend == "LATERAL":
                filters_passed.append(f"Tendencia {trend} == LATERAL")
            elif config.trend_filter == TrendFilter.LATERAL_ONLY:
                filters_failed.append(f"Tendencia {trend} != LATERAL")
            else:
                filters_passed.append("Filtro de tendencia OK")

        elif config.signal_type == SignalType.SELL:
            if score <= (100 - config.min_score):
                filters_passed.append(f"Score {score:.0f} <= {100 - config.min_score}")
            else:
                filters_failed.append(f"Score {score:.0f} > {100 - config.min_score}")

            if config.trend_filter == TrendFilter.DOWN_ONLY and trend == "BAIXA":
                filters_passed.append(f"Tendencia {trend} == BAIXA")
            elif config.trend_filter == TrendFilter.DOWN_ONLY:
                filters_failed.append(f"Tendencia {trend} != BAIXA")
            elif config.trend_filter == TrendFilter.UP_ONLY and trend == "ALTA":
                filters_passed.append(f"Tendencia {trend} == ALTA")
            elif config.trend_filter == TrendFilter.UP_ONLY:
                filters_failed.append(f"Tendencia {trend} != ALTA")
            else:
                filters_passed.append("Filtro de tendencia OK")

        if ConfirmationType.ADX in config.confirmations:
            if adx_val >= config.min_adx:
                filters_passed.append(f"ADX {adx_val:.0f} >= {config.min_adx}")
            else:
                filters_failed.append(f"ADX {adx_val:.0f} < {config.min_adx}")

        if ConfirmationType.RSI in config.confirmations:
            if config.rsi_min <= rsi <= config.rsi_max:
                filters_passed.append(f"RSI {rsi:.1f} entre {config.rsi_min}-{config.rsi_max}")
            else:
                filters_failed.append(f"RSI {rsi:.1f} fora de {config.rsi_min}-{config.rsi_max}")

        if ConfirmationType.VOLUME in config.confirmations:
            if volume_ratio >= config.volume_min_ratio:
                filters_passed.append(f"Volume {volume_ratio:.2f}x >= {config.volume_min_ratio}x")
            else:
                filters_failed.append(f"Volume {volume_ratio:.2f}x < {config.volume_min_ratio}x")

        if ConfirmationType.VWAP in config.confirmations:
            if config.signal_type == SignalType.BUY and vwap_pos == "ACIMA":
                filters_passed.append("Preco acima VWAP")
            elif config.signal_type == SignalType.SELL and vwap_pos == "ABAIXO":
                filters_passed.append("Preco abaixo VWAP")
            else:
                filters_failed.append(f"VWAP posicao {vwap_pos} nao confirma {config.signal_type.value}")

        if ConfirmationType.STOCHASTIC in config.confirmations:
            if config.signal_type == SignalType.BUY and stoch_k < 80:
                filters_passed.append(f"Estocastico K={stoch_k:.0f} nao sobrecomprado")
            elif config.signal_type == SignalType.SELL and stoch_k > 20:
                filters_passed.append(f"Estocastico K={stoch_k:.0f} nao sobrevendido")
            else:
                filters_failed.append(f"Estocastico K={stoch_k:.0f} contradiz {config.signal_type.value}")

        if ConfirmationType.BOLLINGER in config.confirmations:
            if config.signal_type == SignalType.BUY and boll_pos in ("ABAIXO inferior", "FAIXA baixa", "MEIO"):
                filters_passed.append(f"Bollinger {boll_pos} favoravel compra")
            elif config.signal_type == SignalType.SELL and boll_pos in ("ACIMA superior", "FAIXA alta", "MEIO"):
                filters_passed.append(f"Bollinger {boll_pos} favoravel venda")
            else:
                filters_failed.append(f"Bollinger {boll_pos} contradiz {config.signal_type.value}")

        if cross_data and config.min_correlation > 0:
            corr = abs(cross_data.get("correlation_score", 0))
            if corr >= config.min_correlation:
                filters_passed.append(f"Correlacao {corr:.2f} >= {config.min_correlation}")
            else:
                filters_failed.append(f"Correlacao {corr:.2f} < {config.min_correlation}")

        if cross_data and config.max_spread_pct > 0:
            spread = abs(cross_data.get("spread_pct", 0))
            if spread <= config.max_spread_pct:
                filters_passed.append(f"Spread {spread:.2f}% <= {config.max_spread_pct}%")
            else:
                filters_failed.append(f"Spread {spread:.2f}% > {config.max_spread_pct}%")

        total_filters = len(config.confirmations) + 2
        passed = len(filters_passed)
        confidence = (passed / total_filters * 100) if total_filters > 0 else 0

        tick_size = 5.0 if config.asset == "WIN" else 0.50
        if config.signal_type == SignalType.BUY:
            entry = price
            tp = price + config.tp_ticks * tick_size
            sl = price - config.sl_ticks * tick_size
        else:
            entry = price
            tp = price - config.tp_ticks * tick_size
            sl = price + config.sl_ticks * tick_size

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = round(reward / risk, 2) if risk > 0 else 0

        if len(filters_failed) == 0:
            signal = config.signal_type
            reason = f"Estrategia {config.name}: Todos os filtros ({passed}/{total_filters}) confirmados"
        elif len(filters_failed) <= 1 and passed >= total_filters - 1:
            signal = config.signal_type
            reason = f"Estrategia {config.name}: Quase todos os filtros confirmados ({passed}/{total_filters})"
        else:
            signal = SignalType.NEUTRAL
            reason = f"Estrategia {config.name}: {len(filters_failed)} filtros falharam ({passed}/{total_filters})"

        return {
            "strategy": config.name,
            "signal": signal.value,
            "confidence": round(confidence, 1),
            "score": score,
            "entry_price": round(entry, 2),
            "tp_price": round(tp, 2),
            "sl_price": round(sl, 2),
            "risk_reward": rr,
            "filters_passed": filters_passed,
            "filters_failed": filters_failed,
            "reason": reason,
        }

    def evaluate_all(self, analysis_data: dict, cross_data: dict = None) -> List[dict]:
        results = []
        for name, config in self._strategies.items():
            asset_data = analysis_data.get(config.asset, {})
            if asset_data:
                result = self.evaluate(name, asset_data, cross_data)
                results.append(result)
        return results
