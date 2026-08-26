from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List
from enum import Enum


class AlertPriority(str, Enum):
    CRITICAL = "CRITICA"
    HIGH = "ALTA"
    MEDIUM = "MEDIA"
    LOW = "BAIXA"


class AlertCategory(str, Enum):
    SIGNAL = "SINAL"
    PRICE = "PRECO"
    INDICATOR = "INDICADOR"
    RISK = "RISCO"
    STRATEGY = "ESTRATEGIA"
    SYSTEM = "SISTEMA"


@dataclass
class AlertRule:
    name: str
    category: AlertCategory
    priority: AlertPriority
    asset: str
    condition: str
    threshold: float
    enabled: bool = True
    sound: bool = True
    last_triggered: float = 0
    cooldown_seconds: int = 60


@dataclass
class Alert:
    timestamp: float
    rule_name: str
    category: str
    priority: str
    asset: str
    message: str
    value: float
    threshold: float
    sound: bool


class AdvancedAlertSystem:
    def __init__(self) -> None:
        self._rules: List[AlertRule] = []
        self._history: List[Alert] = []
        self._load_defaults()

    def _load_defaults(self) -> None:
        self._rules = [
            AlertRule("COMPRA FORTE", AlertCategory.SIGNAL, AlertPriority.CRITICAL, "WIN", "score>=", 80),
            AlertRule("VENDA FORTE", AlertCategory.SIGNAL, AlertPriority.CRITICAL, "WIN", "score<=", 20),
            AlertRule("COMPRA FORTE WDO", AlertCategory.SIGNAL, AlertPriority.CRITICAL, "WDO", "score>=", 80),
            AlertRule("VENDA FORTE WDO", AlertCategory.SIGNAL, AlertPriority.CRITICAL, "WDO", "score<=", 20),
            AlertRule("RSI SOBRECOMPRADO", AlertCategory.INDICATOR, AlertPriority.HIGH, "WIN", "rsi>=", 75),
            AlertRule("RSI SOBREVENDIDO", AlertCategory.INDICATOR, AlertPriority.HIGH, "WIN", "rsi<=", 25),
            AlertRule("RSI SOBRECOMPRADO WDO", AlertCategory.INDICATOR, AlertPriority.HIGH, "WDO", "rsi>=", 75),
            AlertRule("RSI SOBREVENDIDO WDO", AlertCategory.INDICATOR, AlertPriority.HIGH, "WDO", "rsi<=", 25),
            AlertRule("VOLUME ANORMAL", AlertCategory.INDICATOR, AlertPriority.MEDIUM, "WIN", "volume>=", 2.0),
            AlertRule("VOLUME ANORMAL WDO", AlertCategory.INDICATOR, AlertPriority.MEDIUM, "WDO", "volume>=", 2.0),
            AlertRule("ADX FORTE", AlertCategory.INDICATOR, AlertPriority.MEDIUM, "WIN", "adx>=", 40),
            AlertRule("ADX FORTE WDO", AlertCategory.INDICATOR, AlertPriority.MEDIUM, "WDO", "adx>=", 40),
            AlertRule("ROMPIMENTO RESISTENCIA", AlertCategory.PRICE, AlertPriority.HIGH, "WIN", "price>=", 0),
            AlertRule("PROXIMO SUPORTE", AlertCategory.PRICE, AlertPriority.HIGH, "WIN", "price<=", 0),
            AlertRule("STOP LOSS HIT", AlertCategory.RISK, AlertPriority.CRITICAL, "GERAL", "stop_hit", 0),
            AlertRule("LIMITE DIARIO", AlertCategory.RISK, AlertPriority.CRITICAL, "GERAL", "daily_limit", 0),
            AlertRule("DIVERGENCIA FORTE", AlertCategory.INDICATOR, AlertPriority.HIGH, "GERAL", "divergence", 0),
            AlertRule("CONFLUENCIA MTF", AlertCategory.STRATEGY, AlertPriority.HIGH, "GERAL", "mtf_confluence", 0),
        ]

    def check_alerts(self, analysis_data: dict, cross_data: dict = None, risk_data: dict = None) -> List[dict]:
        now = time.time()
        triggered = []

        for rule in self._rules:
            if not rule.enabled:
                continue
            if now - rule.last_triggered < rule.cooldown_seconds:
                continue

            asset = rule.asset
            if asset in ("WIN", "WDO"):
                data = analysis_data.get(asset, {})
                if not data:
                    continue
            elif asset == "GERAL":
                data = analysis_data
            else:
                continue

            value = 0
            threshold = rule.threshold
            should_trigger = False
            message = ""

            if rule.condition == "score>=":
                value = data.get("score", 50)
                if value >= threshold:
                    should_trigger = True
                    message = f"{asset} com score {value:.0f}/100. Sinal de compra forte!"
            elif rule.condition == "score<=":
                value = data.get("score", 50)
                if value <= threshold:
                    should_trigger = True
                    message = f"{asset} com score {value:.0f}/100. Sinal de venda forte!"
            elif rule.condition == "rsi>=":
                value = data.get("rsi", 50)
                if value >= threshold:
                    should_trigger = True
                    message = f"{asset} com RSI {value:.1f}. Zona de sobrecompra!"
            elif rule.condition == "rsi<=":
                value = data.get("rsi", 50)
                if value <= threshold:
                    should_trigger = True
                    message = f"{asset} com RSI {value:.1f}. Zona de sobrevenda!"
            elif rule.condition == "volume>=":
                value = data.get("volume_ratio", 1)
                if value >= threshold:
                    should_trigger = True
                    message = f"{asset} com volume {value:.2f}x acima da media!"
            elif rule.condition == "adx>=":
                adx_data = data.get("adx", {})
                value = adx_data.get("adx", 0) if isinstance(adx_data, dict) else 0
                if value >= threshold:
                    should_trigger = True
                    message = f"{asset} com ADX {value:.0f}. Tendencia forte!"

            if should_trigger:
                rule.last_triggered = now
                alert = {
                    "timestamp": time.strftime("%H:%M:%S", time.localtime(now)),
                    "rule": rule.name,
                    "category": rule.category.value,
                    "priority": rule.priority.value,
                    "asset": asset,
                    "message": message,
                    "value": round(value, 2),
                    "threshold": threshold,
                    "sound": rule.sound,
                }
                triggered.append(alert)
                self._history.append(Alert(
                    timestamp=now,
                    rule_name=rule.name,
                    category=rule.category.value,
                    priority=rule.priority.value,
                    asset=asset,
                    message=message,
                    value=value,
                    threshold=threshold,
                    sound=rule.sound,
                ))

        return triggered

    def get_all_alerts(self, limit: int = 30) -> List[dict]:
        recent = self._history[-limit:]
        return [{
            "timestamp": time.strftime("%H:%M:%S", time.localtime(a.timestamp)),
            "rule": a.rule_name,
            "category": a.category,
            "priority": a.priority,
            "asset": a.asset,
            "message": a.message,
            "sound": a.sound,
        } for a in reversed(recent)]

    def get_rules(self) -> List[dict]:
        return [{
            "name": r.name,
            "category": r.category.value,
            "priority": r.priority.value,
            "asset": r.asset,
            "enabled": r.enabled,
            "sound": r.sound,
            "condition": r.condition,
            "threshold": r.threshold,
        } for r in self._rules]

    def toggle_rule(self, rule_name: str, enabled: bool) -> bool:
        for r in self._rules:
            if r.name == rule_name:
                r.enabled = enabled
                return True
        return False

    def clear_history(self) -> None:
        self._history.clear()
