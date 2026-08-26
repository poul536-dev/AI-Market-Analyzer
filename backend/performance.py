from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List


@dataclass
class Trade:
    timestamp: float
    asset: str
    direction: str
    entry_price: float
    exit_price: float
    contracts: int
    pnl: float
    strategy: str
    stop_hit: bool = False
    target_hit: bool = False
    duration_seconds: float = 0


@dataclass
class PerformanceSnapshot:
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    best_trade: float
    worst_trade: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    current_drawdown: float
    consecutive_wins: int
    consecutive_losses: int
    avg_win: float
    avg_loss: float
    expectancy: float
    recovery_factor: float
    equity_curve: List[dict]
    win_streak: int
    loss_streak: int
    avg_duration: float
    monthly_returns: dict


class PerformanceTracker:
    def __init__(self) -> None:
        self._trades: List[Trade] = []
        self._equity_curve: List[dict] = []
        self._initial_balance: float = 100000.0
        self._current_balance: float = 100000.0
        self._peak_balance: float = 100000.0

    def add_trade(self, trade: Trade) -> None:
        self._trades.append(trade)
        self._current_balance += trade.pnl
        self._peak_balance = max(self._peak_balance, self._current_balance)
        self._equity_curve.append({
            "timestamp": trade.timestamp,
            "balance": round(self._current_balance, 2),
            "pnl": round(trade.pnl, 2),
        })

    def get_snapshot(self) -> dict:
        if not self._trades:
            return self._empty_snapshot()

        wins = [t for t in self._trades if t.pnl > 0]
        losses = [t for t in self._trades if t.pnl < 0]
        breakeven = [t for t in self._trades if t.pnl == 0]

        total = len(self._trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total * 100) if total > 0 else 0

        total_pnl = sum(t.pnl for t in self._trades)
        avg_pnl = total_pnl / total if total > 0 else 0

        best = max((t.pnl for t in self._trades), default=0)
        worst = min((t.pnl for t in self._trades), default=0)

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0

        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        returns = [t.pnl / self._initial_balance for t in self._trades]
        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
            sharpe = round((avg_return / std_return) * math.sqrt(252), 2) if std_return > 0 else 0
        else:
            sharpe = 0

        peak = self._initial_balance
        max_dd = 0
        max_dd_pct = 0
        current_dd = 0
        balance = self._initial_balance
        for t in self._trades:
            balance += t.pnl
            peak = max(peak, balance)
            dd = peak - balance
            dd_pct = (dd / peak * 100) if peak > 0 else 0
            max_dd = max(max_dd, dd)
            max_dd_pct = max(max_dd_pct, dd_pct)
            current_dd = dd

        max_dd_pct = round(max_dd_pct, 2)
        current_dd = round(current_dd, 2)

        win_streak = 0
        loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        current_wins = 0
        current_losses = 0

        for t in self._trades:
            if t.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_win_streak = max(max_win_streak, current_wins)
            elif t.pnl < 0:
                current_losses += 1
                current_wins = 0
                max_loss_streak = max(max_loss_streak, current_losses)
            else:
                current_wins = 0
                current_losses = 0

        win_streak = max_win_streak
        loss_streak = max_loss_streak

        avg_duration = sum(t.duration_seconds for t in self._trades) / total if total > 0 else 0

        monthly = {}
        for t in self._trades:
            month_key = time.strftime("%Y-%m", time.localtime(t.timestamp))
            if month_key not in monthly:
                monthly[month_key] = {"pnl": 0, "trades": 0, "wins": 0}
            monthly[month_key]["pnl"] += t.pnl
            monthly[month_key]["trades"] += 1
            if t.pnl > 0:
                monthly[month_key]["wins"] += 1

        for m in monthly:
            monthly[m]["pnl"] = round(monthly[m]["pnl"], 2)
            monthly[m]["win_rate"] = round(monthly[m]["wins"] / monthly[m]["trades"] * 100, 1) if monthly[m]["trades"] > 0 else 0

        return {
            "total_trades": total,
            "wins": win_count,
            "losses": loss_count,
            "breakeven": len(breakeven),
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "best_trade": round(best, 2),
            "worst_trade": round(worst, 2),
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": max_dd_pct,
            "current_drawdown": current_dd,
            "consecutive_wins": win_streak,
            "consecutive_losses": loss_streak,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 4),
            "recovery_factor": round(total_pnl / max_dd, 2) if max_dd > 0 else 0,
            "equity_curve": self._equity_curve[-50:],
            "monthly_returns": monthly,
            "current_balance": round(self._current_balance, 2),
            "initial_balance": self._initial_balance,
            "total_return_pct": round((self._current_balance - self._initial_balance) / self._initial_balance * 100, 2),
        }

    def _empty_snapshot(self) -> dict:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_pnl": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "profit_factor": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "max_drawdown_pct": 0,
            "current_drawdown": 0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "expectancy": 0,
            "recovery_factor": 0,
            "equity_curve": [],
            "monthly_returns": {},
            "current_balance": self._initial_balance,
            "initial_balance": self._initial_balance,
            "total_return_pct": 0,
        }

    def get_trades(self, limit: int = 20) -> List[dict]:
        recent = self._trades[-limit:]
        return [{
            "timestamp": time.strftime("%d/%m %H:%M", time.localtime(t.timestamp)),
            "asset": t.asset,
            "direction": t.direction,
            "entry": t.entry_price,
            "exit": t.exit_price,
            "pnl": round(t.pnl, 2),
            "contracts": t.contracts,
            "strategy": t.strategy,
        } for t in reversed(recent)]

    def clear(self) -> None:
        self._trades.clear()
        self._equity_curve.clear()
        self._current_balance = self._initial_balance
        self._peak_balance = self._initial_balance
