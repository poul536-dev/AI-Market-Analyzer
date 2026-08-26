from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

from config import settings, ScoreWeights

log = logging.getLogger("auto_tune")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
WEIGHTS_HISTORY_FILE = os.path.join(DATA_DIR, "weights_history.json")

DEFAULT_WEIGHTS = {
    "vwap": 0.15,
    "trend": 0.15,
    "moving_averages": 0.12,
    "momentum": 0.12,
    "volume": 0.08,
    "breakout": 0.08,
    "structure": 0.05,
    "relative_strength": 0.05,
    "adx": 0.10,
    "stochastic": 0.05,
    "bollinger": 0.05,
}

COMPONENT_NAMES = list(DEFAULT_WEIGHTS.keys())

MIN_SAMPLES = 15
LEARNING_RATE = 0.08
MIN_WEIGHT = 0.02
MAX_WEIGHT = 0.30
TUNE_INTERVAL = 600


class AutoTuner:
    def __init__(self) -> None:
        self._current_weights: dict = dict(DEFAULT_WEIGHTS)
        self._last_tune_time: float = 0.0
        self._tune_history: list = []
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load_history()

    def _load_history(self) -> None:
        try:
            if os.path.exists(WEIGHTS_HISTORY_FILE):
                with open(WEIGHTS_HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    self._tune_history = data.get("history", [])
                    if data.get("current"):
                        self._current_weights = data["current"]
        except Exception as e:
            log.warning("Error loading weights history: %s", e)

    def _save_history(self) -> None:
        try:
            with open(WEIGHTS_HISTORY_FILE, "w") as f:
                json.dump({
                    "current": self._current_weights,
                    "history": self._tune_history[-50:],
                }, f, indent=1)
        except Exception as e:
            log.error("Error saving weights history: %s", e)

    def get_weights(self) -> ScoreWeights:
        w = self._current_weights
        return ScoreWeights(
            vwap=w.get("vwap", 0.15),
            trend=w.get("trend", 0.15),
            moving_averages=w.get("moving_averages", 0.12),
            momentum=w.get("momentum", 0.12),
            volume=w.get("volume", 0.08),
            breakout=w.get("breakout", 0.08),
            structure=w.get("structure", 0.05),
            relative_strength=w.get("relative_strength", 0.05),
            adx=w.get("adx", 0.10),
            stochastic=w.get("stochastic", 0.05),
            bollinger=w.get("bollinger", 0.05),
        )

    def tune(self, accuracy_data: dict) -> dict:
        now = time.time()
        if (now - self._last_tune_time) < TUNE_INTERVAL:
            return {"tuned": False, "reason": "cooldown"}

        total = accuracy_data.get("total_predictions", 0)
        if total < MIN_SAMPLES:
            return {
                "tuned": False,
                "reason": "insufficient_data",
                "current": total,
                "needed": MIN_SAMPLES,
            }

        component_acc = accuracy_data.get("component_accuracy", {})
        if not component_acc:
            return {"tuned": False, "reason": "no_component_data"}

        changes = {}
        new_weights = dict(self._current_weights)

        for comp in COMPONENT_NAMES:
            if comp not in component_acc:
                continue

            comp_data = component_acc[comp]
            accuracy = comp_data.get("accuracy", 50)
            comp_total = comp_data.get("total", 0)

            if comp_total < 5:
                continue

            current_w = new_weights.get(comp, DEFAULT_WEIGHTS.get(comp, 0.1))

            if accuracy > 60:
                adjustment = LEARNING_RATE * (accuracy - 50) / 50
                new_w = current_w + adjustment
            elif accuracy < 40:
                adjustment = LEARNING_RATE * (50 - accuracy) / 50
                new_w = current_w - adjustment
            else:
                continue

            new_w = max(MIN_WEIGHT, min(MAX_WEIGHT, new_w))
            new_w = round(new_w, 4)

            if abs(new_w - current_w) > 0.001:
                changes[comp] = {
                    "old": current_w,
                    "new": new_w,
                    "accuracy": accuracy,
                    "samples": comp_total,
                }
                new_weights[comp] = new_w

        if not changes:
            return {"tuned": False, "reason": "no_significant_changes"}

        total_weight = sum(new_weights.values())
        for comp in new_weights:
            new_weights[comp] = round(new_weights[comp] / total_weight, 4)

        self._current_weights = new_weights
        self._last_tune_time = now

        self._apply_to_settings()

        tune_record = {
            "timestamp": now,
            "changes": changes,
            "overall_win_rate": accuracy_data.get("win_rate", 0),
            "new_weights": dict(new_weights),
        }
        self._tune_history.append(tune_record)
        self._save_history()

        log.info("Auto-tune applied: %d component weights adjusted", len(changes))

        return {
            "tuned": True,
            "changes": changes,
            "new_weights": dict(new_weights),
            "overall_win_rate": accuracy_data.get("win_rate", 0),
        }

    def _apply_to_settings(self) -> None:
        w = self._current_weights
        settings.score_weights.vwap = w.get("vwap", 0.15)
        settings.score_weights.trend = w.get("trend", 0.15)
        settings.score_weights.moving_averages = w.get("moving_averages", 0.12)
        settings.score_weights.momentum = w.get("momentum", 0.12)
        settings.score_weights.volume = w.get("volume", 0.08)
        settings.score_weights.breakout = w.get("breakout", 0.08)
        settings.score_weights.structure = w.get("structure", 0.05)
        settings.score_weights.relative_strength = w.get("relative_strength", 0.05)
        settings.score_weights.adx = w.get("adx", 0.10)
        settings.score_weights.stochastic = w.get("stochastic", 0.05)
        settings.score_weights.bollinger = w.get("bollinger", 0.05)

    def reset_weights(self) -> None:
        self._current_weights = dict(DEFAULT_WEIGHTS)
        self._apply_to_settings()
        self._tune_history = []
        self._save_history()

    def get_current_weights(self) -> dict:
        return {
            "current": dict(self._current_weights),
            "defaults": dict(DEFAULT_WEIGHTS),
            "history_count": len(self._tune_history),
            "last_tune": self._last_tune_time,
        }

    def get_tune_history(self, limit: int = 10) -> list:
        return list(reversed(self._tune_history[-limit:]))
