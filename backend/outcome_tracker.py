from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

log = logging.getLogger("outcome_tracker")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "predictions.json")
OUTCOMES_FILE = os.path.join(DATA_DIR, "outcomes.json")
ACCURACY_CACHE_FILE = os.path.join(DATA_DIR, "accuracy_cache.json")


@dataclass
class Prediction:
    id: str
    asset: str
    timestamp: float
    price_at_prediction: float
    score: int
    signal: str
    components: dict
    direction: str
    sentiment_score: float
    relevance: float
    resolved: bool = False
    actual_outcome: str = ""
    price_at_resolution: float = 0.0
    resolution_timestamp: float = 0.0
    profit_points: float = 0.0


class OutcomeTracker:
    def __init__(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        self._predictions: List[Prediction] = []
        self._outcomes: List[dict] = []
        self._load_data()

    def _load_data(self) -> None:
        try:
            if os.path.exists(PREDICTIONS_FILE):
                with open(PREDICTIONS_FILE, "r") as f:
                    raw = json.load(f)
                    self._predictions = [Prediction(**p) for p in raw]
        except Exception as e:
            log.warning("Error loading predictions: %s", e)
            self._predictions = []

        try:
            if os.path.exists(OUTCOMES_FILE):
                with open(OUTCOMES_FILE, "r") as f:
                    self._outcomes = json.load(f)
        except Exception as e:
            log.warning("Error loading outcomes: %s", e)
            self._outcomes = []

    def _save_predictions(self) -> None:
        try:
            with open(PREDICTIONS_FILE, "w") as f:
                json.dump([asdict(p) for p in self._predictions[-500:]], f, indent=1)
        except Exception as e:
            log.error("Error saving predictions: %s", e)

    def _save_outcomes(self) -> None:
        try:
            with open(OUTCOMES_FILE, "w") as f:
                json.dump(self._outcomes[-500:], f, indent=1)
        except Exception as e:
            log.error("Error saving outcomes: %s", e)

    def record_prediction(
        self,
        asset: str,
        price: float,
        score: int,
        signal: str,
        components: dict,
        sentiment_score: float = 0.0,
        relevance: float = 0.0,
    ) -> str:
        pred_id = "%s_%d_%d" % (asset, int(time.time()), score)

        if score > 60:
            direction = "UP"
        elif score < 40:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"

        pred = Prediction(
            id=pred_id,
            asset=asset,
            timestamp=time.time(),
            price_at_prediction=price,
            score=score,
            signal=signal,
            components=components,
            direction=direction,
            sentiment_score=sentiment_score,
            relevance=relevance,
        )

        self._predictions.append(pred)
        self._save_predictions()
        return pred_id

    def resolve_predictions(self, current_prices: dict) -> List[dict]:
        """Check pending predictions and resolve them with actual outcomes."""
        TICK_SIZE_WIN = 5.0
        TICK_SIZE_WDO = 0.50

        resolved = []
        for pred in self._predictions:
            if pred.resolved:
                continue

            elapsed = time.time() - pred.timestamp
            if elapsed < 60:
                continue

            current_price = current_prices.get(pred.asset, 0)
            if current_price <= 0:
                continue

            pred.resolved = True
            pred.price_at_resolution = current_price
            pred.resolution_timestamp = time.time()
            pred.profit_points = current_price - pred.price_at_prediction

            tick_size = TICK_SIZE_WIN if pred.asset == "WIN" else TICK_SIZE_WDO

            if pred.direction == "UP":
                pred.actual_outcome = "WIN" if pred.profit_points > 0 else "LOSS"
            elif pred.direction == "DOWN":
                pred.actual_outcome = "WIN" if pred.profit_points < 0 else "LOSS"
            else:
                pred.actual_outcome = "NEUTRAL"

            outcome_record = {
                "prediction_id": pred.id,
                "asset": pred.asset,
                "direction": pred.direction,
                "score": pred.score,
                "price_prediction": pred.price_at_prediction,
                "price_outcome": current_price,
                "profit_points": round(pred.profit_points, 2),
                "ticks": round(pred.profit_points / tick_size, 1) if tick_size > 0 else 0,
                "outcome": pred.actual_outcome,
                "components": pred.components,
                "sentiment_score": pred.sentiment_score,
                "resolved_at": pred.resolution_timestamp,
            }

            self._outcomes.append(outcome_record)
            resolved.append(outcome_record)

        if resolved:
            self._save_predictions()
            self._save_outcomes()

        return resolved

    def get_accuracy(self, limit: int = 100) -> dict:
        outcomes = self._outcomes[-limit:]
        if not outcomes:
            return self._empty_accuracy()

        total = len(outcomes)
        wins = sum(1 for o in outcomes if o["outcome"] == "WIN")
        losses = sum(1 for o in outcomes if o["outcome"] == "LOSS")
        neutrals = sum(1 for o in outcomes if o["outcome"] == "NEUTRAL")

        win_rate = round((wins / max(total - neutrals, 1)) * 100, 1)

        wins_up = sum(1 for o in outcomes if o["outcome"] == "WIN" and o["direction"] == "UP")
        total_up = sum(1 for o in outcomes if o["direction"] == "UP")
        wins_down = sum(1 for o in outcomes if o["outcome"] == "WIN" and o["direction"] == "DOWN")
        total_down = sum(1 for o in outcomes if o["direction"] == "DOWN")

        total_ticks = sum(abs(o.get("ticks", 0)) for o in outcomes)
        profit_ticks = sum(o.get("ticks", 0) for o in outcomes if o["outcome"] == "WIN")
        loss_ticks = sum(abs(o.get("ticks", 0)) for o in outcomes if o["outcome"] == "LOSS")

        avg_profit = round(profit_ticks / max(wins, 1), 1)
        avg_loss = round(loss_ticks / max(losses, 1), 1)

        component_accuracy = self._calc_component_accuracy(outcomes)

        score_buckets = {}
        for o in outcomes:
            bucket = "HIGH" if o["score"] >= 60 else "LOW" if o["score"] <= 40 else "MID"
            if bucket not in score_buckets:
                score_buckets[bucket] = {"wins": 0, "total": 0}
            if o["outcome"] != "NEUTRAL":
                score_buckets[bucket]["total"] += 1
                if o["outcome"] == "WIN":
                    score_buckets[bucket]["wins"] += 1

        sentiment_accuracy = self._calc_sentiment_accuracy(outcomes)

        return {
            "total_predictions": total,
            "wins": wins,
            "losses": losses,
            "neutrals": neutrals,
            "win_rate": win_rate,
            "win_rate_up": round((wins_up / max(total_up, 1)) * 100, 1),
            "win_rate_down": round((wins_down / max(total_down, 1)) * 100, 1),
            "avg_profit_ticks": avg_profit,
            "avg_loss_ticks": avg_loss,
            "profit_factor": round(profit_ticks / max(loss_ticks, 1), 2),
            "component_accuracy": component_accuracy,
            "score_buckets": {
                k: {
                    "total": v["total"],
                    "wins": v["wins"],
                    "win_rate": round((v["wins"] / max(v["total"], 1)) * 100, 1),
                }
                for k, v in score_buckets.items()
            },
            "sentiment_accuracy": sentiment_accuracy,
        }

    def _calc_component_accuracy(self, outcomes: List[dict]) -> dict:
        components = {}
        component_names = [
            "vwap", "trend", "moving_averages", "momentum", "volume",
            "breakout", "structure", "relative_strength", "adx", "stochastic", "bollinger",
        ]

        for comp in component_names:
            correct = 0
            total = 0
            for o in outcomes:
                if o["outcome"] == "NEUTRAL":
                    continue
                comp_val = o.get("components", {}).get(comp, 50)
                direction = o.get("direction", "NEUTRAL")

                if direction == "UP" and comp_val > 55:
                    correct += 1
                elif direction == "DOWN" and comp_val < 45:
                    correct += 1
                total += 1

            accuracy = round((correct / max(total, 1)) * 100, 1)
            components[comp] = {
                "accuracy": accuracy,
                "correct": correct,
                "total": total,
            }

        return components

    def _calc_sentiment_accuracy(self, outcomes: List[dict]) -> dict:
        aligned = 0
        total = 0
        for o in outcomes:
            if o["outcome"] == "NEUTRAL":
                continue
            sent = o.get("sentiment_score", 0)
            direction = o.get("direction", "NEUTRAL")

            if direction == "UP" and sent > 5:
                aligned += 1
            elif direction == "DOWN" and sent < -5:
                aligned += 1
            total += 1

        return {
            "aligned": aligned,
            "total": total,
            "accuracy": round((aligned / max(total, 1)) * 100, 1),
        }

    def _empty_accuracy(self) -> dict:
        return {
            "total_predictions": 0,
            "wins": 0,
            "losses": 0,
            "neutrals": 0,
            "win_rate": 0,
            "win_rate_up": 0,
            "win_rate_down": 0,
            "avg_profit_ticks": 0,
            "avg_loss_ticks": 0,
            "profit_factor": 0,
            "component_accuracy": {},
            "score_buckets": {},
            "sentiment_accuracy": {"aligned": 0, "total": 0, "accuracy": 0},
        }

    def get_pending_count(self) -> int:
        return sum(1 for p in self._predictions if not p.resolved)

    def get_history(self, limit: int = 20) -> List[dict]:
        outcomes = self._outcomes[-limit:]
        return list(reversed(outcomes))

    def clear(self) -> None:
        self._predictions = []
        self._outcomes = []
        self._save_predictions()
        self._save_outcomes()
