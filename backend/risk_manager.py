from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    account_balance: float = 100000.0
    risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 3.0
    max_daily_trades: int = 5
    max_open_positions: int = 2
    max_drawdown_pct: float = 10.0
    min_risk_reward: float = 1.5
    win_size_multiplier: float = 1.5
    loss_size_multiplier: float = 0.5
    cooldown_minutes: int = 30


@dataclass
class RiskAssessment:
    position_size: float
    contracts: int
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float
    daily_loss_remaining: float
    daily_trades_remaining: int
    can_trade: bool
    stop_type: str
    warning: str
    suggestion: str


class RiskManager:
    def __init__(self, config: RiskConfig = None) -> None:
        self._config = config or RiskConfig()
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._consecutive_losses = 0
        self._consecutive_wins = 0
        self._last_trade_time = 0.0

    def reset_daily(self) -> None:
        self._daily_pnl = 0.0
        self._daily_trades = 0

    def update_after_trade(self, pnl: float, trade_time: float) -> None:
        self._daily_pnl += pnl
        self._daily_trades += 1
        self._last_trade_time = trade_time

        if pnl < 0:
            self._consecutive_losses += 1
            self._consecutive_wins = 0
        elif pnl > 0:
            self._consecutive_wins += 1
            self._consecutive_losses = 0
        else:
            self._consecutive_losses = 0
            self._consecutive_wins = 0

    def assess_risk(
        self,
        entry_price: float,
        stop_price: float,
        target_price: float,
        asset: str,
        current_price: float = None,
    ) -> dict:
        tick_size = 5.0 if asset == "WIN" else 0.50
        tick_value = 0.50 if asset == "WIN" else 0.10

        risk_ticks = abs(entry_price - stop_price) / tick_size
        reward_ticks = abs(target_price - entry_price) / tick_size

        risk_per_contract = risk_ticks * tick_value
        reward_per_contract = reward_ticks * tick_value

        risk_amount_per = risk_per_contract
        reward_amount_per = reward_per_contract

        base_risk = self._config.account_balance * (self._config.risk_per_trade_pct / 100)

        if self._consecutive_losses >= 3:
            adjusted_risk = base_risk * self._config.loss_size_multiplier
            warning = f"ATENCAO: {self._consecutive_losses} derrotas consecutivas. Risco reduzido para {self._config.loss_size_multiplier*100:.0f}%."
        elif self._consecutive_wins >= 3:
            adjusted_risk = base_risk * self._config.win_size_multiplier
            warning = f"ALERTA: {self._consecutive_wins} vitorias consecutivas. Risco aumentado para {self._config.win_size_multiplier*100:.0f}%."
        else:
            adjusted_risk = base_risk
            warning = ""

        if risk_per_contract > 0:
            contracts = max(1, int(adjusted_risk / risk_per_contract))
        else:
            contracts = 1

        total_risk = risk_per_contract * contracts
        total_reward = reward_per_contract * contracts
        rr_ratio = round(total_reward / total_risk, 2) if total_risk > 0 else 0

        daily_loss_remaining = self._config.account_balance * (self._config.max_daily_loss_pct / 100) + self._daily_pnl
        daily_trades_remaining = self._config.max_daily_trades - self._daily_trades

        can_trade = True
        suggestion = ""

        if daily_loss_remaining <= 0:
            can_trade = False
            suggestion = "Limite diario de perda atingido. Pare de operar hoje."
        elif daily_trades_remaining <= 0:
            can_trade = False
            suggestion = f"Limite de {self._config.max_daily_trades} operacoes/dia atingido."
        elif rr_ratio < self._config.min_risk_reward:
            can_trade = False
            suggestion = f"Risk/Reward {rr_ratio:.2f} menor que o minimo {self._config.min_risk_reward}."
        elif self._consecutive_losses >= 5:
            can_trade = False
            suggestion = "5 derrotas consecutivas. Considere uma pausa."
        elif risk_per_contract > adjusted_risk:
            contracts = 1
            suggestion = "Posicao minima (1 contrato) - risco excede o limite."
        else:
            suggestion = f"Operacao dentro dos parametros. {contracts} contrato(s)."

        stop_type = "FIXO"
        if risk_per_contract > 0 and risk_per_contract < 10:
            stop_type = "APERTADO"
        elif risk_per_contract > 50:
            stop_type = "AMPLO"

        return {
            "position_size": round(total_risk, 2),
            "contracts": contracts,
            "risk_per_contract": round(risk_per_contract, 2),
            "reward_per_contract": round(reward_per_contract, 2),
            "risk_amount": round(total_risk, 2),
            "reward_amount": round(total_reward, 2),
            "risk_reward_ratio": rr_ratio,
            "daily_loss_remaining": round(daily_loss_remaining, 2),
            "daily_trades_remaining": daily_trades_remaining,
            "daily_pnl": round(self._daily_pnl, 2),
            "consecutive_losses": self._consecutive_losses,
            "consecutive_wins": self._consecutive_wins,
            "can_trade": can_trade,
            "stop_type": stop_type,
            "warning": warning,
            "suggestion": suggestion,
        }

    def get_position_suggestion(
        self,
        asset: str,
        entry_price: float,
        confidence: float,
        trend: str,
    ) -> dict:
        tick_size = 5.0 if asset == "WIN" else 0.50
        tick_value = 0.50 if asset == "WIN" else 0.10

        if confidence >= 80:
            rr_target = 2.0
            sl_ticks = 5
        elif confidence >= 60:
            rr_target = 1.5
            sl_ticks = 8
        else:
            rr_target = 1.2
            sl_ticks = 10

        tp_ticks = int(sl_ticks * rr_target)

        if trend == "ALTA":
            sl_price = entry_price - sl_ticks * tick_size
            tp_price = entry_price + tp_ticks * tick_size
        elif trend == "BAIXA":
            sl_price = entry_price + sl_ticks * tick_size
            tp_price = entry_price - tp_ticks * tick_size
        else:
            sl_price = entry_price - sl_ticks * tick_size
            tp_price = entry_price + tp_ticks * tick_size

        return {
            "entry": round(entry_price, 2),
            "sl": round(sl_price, 2),
            "tp": round(tp_price, 2),
            "sl_ticks": sl_ticks,
            "tp_ticks": tp_ticks,
            "risk_reward": rr_target,
            "trend": trend,
            "confidence": confidence,
        }
