from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class SentimentData:
    source: str
    label: str
    score: float
    detail: str
    timestamp: float


class MarketSentiment:
    def __init__(self) -> None:
        self._cache: dict = {}
        self._cache_time: float = 0
        self._cache_ttl: float = 300

    def analyze(self, global_data: dict, win_data: dict = None, wdo_data: dict = None) -> dict:
        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        factors = []
        overall_score = 50.0

        if global_data:
            ibov = global_data.get("IBOV", {})
            if ibov:
                ibov_change = ((ibov.get("price", 0) - ibov.get("open", 1)) / max(ibov.get("open", 1), 1)) * 100
                if ibov_change > 0.5:
                    factors.append({"factor": "IBOV", "impact": "POSITIVO", "detail": f"IBOV +{ibov_change:.2f}%", "score": 65})
                    overall_score += 5
                elif ibov_change < -0.5:
                    factors.append({"factor": "IBOV", "impact": "NEGATIVO", "detail": f"IBOV {ibov_change:.2f}%", "score": 35})
                    overall_score -= 5
                else:
                    factors.append({"factor": "IBOV", "impact": "NEUTRO", "detail": f"IBOV {ibov_change:+.2f}%", "score": 50})

            sp500 = global_data.get("SP500", {})
            if sp500:
                sp_change = ((sp500.get("price", 0) - sp500.get("open", 1)) / max(sp500.get("open", 1), 1)) * 100
                if sp_change > 0.3:
                    factors.append({"factor": "S&P500", "impact": "POSITIVO", "detail": f"S&P500 +{sp_change:.2f}%", "score": 60})
                    overall_score += 3
                elif sp_change < -0.3:
                    factors.append({"factor": "S&P500", "impact": "NEGATIVO", "detail": f"S&P500 {sp_change:.2f}%", "score": 40})
                    overall_score -= 3

            vix = global_data.get("VIX", {})
            if vix:
                vix_val = vix.get("price", 0)
                if vix_val > 30:
                    factors.append({"factor": "VIX", "impact": "NEGATIVO", "detail": f"VIX {vix_val:.1f} (Medo alto)", "score": 30})
                    overall_score -= 8
                elif vix_val > 20:
                    factors.append({"factor": "VIX", "impact": "NEUTRO", "detail": f"VIX {vix_val:.1f} (Normal)", "score": 45})
                    overall_score -= 2
                else:
                    factors.append({"factor": "VIX", "impact": "POSITIVO", "detail": f"VIX {vix_val:.1f} (Calmo)", "score": 60})
                    overall_score += 5

            oil = global_data.get("OIL", {})
            if oil:
                oil_change = ((oil.get("price", 0) - oil.get("open", 1)) / max(oil.get("open", 1), 1)) * 100
                if oil_change > 1:
                    factors.append({"factor": "Petroleo", "impact": "MISTO", "detail": f"Petroleo +{oil_change:.2f}% (inflacao)", "score": 45})
                elif oil_change < -1:
                    factors.append({"factor": "Petroleo", "impact": "POSITIVO", "detail": f"Petroleo {oil_change:.2f}% (desinflacao)", "score": 55})
                    overall_score += 2

            dxy = global_data.get("DXY", {})
            usdbrl = global_data.get("USDBRL", {})
            if usdbrl:
                usd_change = ((usdbrl.get("price", 0) - usdbrl.get("open", 1)) / max(usdbrl.get("open", 1), 1)) * 100
                if usd_change > 0.5:
                    factors.append({"factor": "USD/BRL", "impact": "NEGATIVO WIN", "detail": f"Dolar +{usd_change:.2f}% (pressao WIN)", "score": 35})
                    overall_score -= 4
                elif usd_change < -0.5:
                    factors.append({"factor": "USD/BRL", "impact": "POSITIVO WIN", "detail": f"Dolar {usd_change:.2f}% (favorece WIN)", "score": 65})
                    overall_score += 4

            us10y = global_data.get("US10Y", {})
            if us10y:
                yield_val = us10y.get("price", 0)
                if yield_val > 5:
                    factors.append({"factor": "Juros US 10y", "impact": "NEGATIVO", "detail": f"Yield {yield_val:.2f}% (alto)", "score": 35})
                    overall_score -= 3
                elif yield_val < 4:
                    factors.append({"factor": "Juros US 10y", "impact": "POSITIVO", "detail": f"Yield {yield_val:.2f}% (baixo)", "score": 60})
                    overall_score += 3

        if win_data:
            win_trend = win_data.get("tendencia", "LATERAL")
            win_score = win_data.get("score", 50)
            if win_trend == "ALTA" and win_score > 60:
                factors.append({"factor": "WIN Tecnico", "impact": "POSITIVO", "detail": f"WIN {win_trend} score {win_score}", "score": 65})
                overall_score += 3
            elif win_trend == "BAIXA" and win_score < 40:
                factors.append({"factor": "WIN Tecnico", "impact": "NEGATIVO", "detail": f"WIN {win_trend} score {win_score}", "score": 35})
                overall_score -= 3

        overall_score = max(0, min(100, overall_score))

        if overall_score >= 65:
            label = "otimista"
            interpretation = "Ambiente favoravel a compras. Mercados globais e indicadores alinhados positivamente."
        elif overall_score >= 55:
            label = "levemente otimista"
            interpretation = "Leve viés comprador. Alguns fatores positivos, mas sem convicção forte."
        elif overall_score <= 35:
            label = "pessimista"
            interpretation = "Ambiente favoravel a vendas. Pressao vendedora nos mercados."
        elif overall_score <= 45:
            label = "levemente pessimista"
            interpretation = "Leve viés vendedor. Alguns fatores negativos presentes."
        else:
            label = "neutro"
            interpretation = "Mercado sem direcao clara. Fatores mistos. Cuidado com operacoes."

        result = {
            "overall_score": round(overall_score, 1),
            "label": label,
            "interpretation": interpretation,
            "factors": factors,
            "factor_count": len(factors),
            "positive_count": sum(1 for f in factors if "POSITIVO" in f["impact"]),
            "negative_count": sum(1 for f in factors if "NEGATIVO" in f["impact"]),
            "neutral_count": sum(1 for f in factors if f["impact"] in ("NEUTRO", "MISTO")),
            "timestamp": time.strftime("%H:%M:%S"),
        }

        self._cache = result
        self._cache_time = now
        return result
