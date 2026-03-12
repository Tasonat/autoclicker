"""
core/humanizer.py — Anti-detection humanization layer.

Generates randomized delays and mouse micro-movements to simulate human behaviour.
"""

from __future__ import annotations

import random
import math
from config.settings import Settings

# Jitter radius in pixels for each intensity level
_JITTER_RADIUS = {
    "none": 0,
    "low": 3,
    "medium": 8,
}

# Every ~30-60 clicks insert a longer "micro-pause" (200-600 ms extra)
_PAUSE_CHANCE = 0.03  # 3 % chance per click


class Humanizer:
    """Produce human-like delay and jitter values based on current settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def update_settings(self, settings: Settings) -> None:
        self._settings = settings

    # --- public API ---

    def next_delay(self) -> float:
        """Return the next delay **in seconds**, drawn from [min, max] + optional variance."""
        lo = self._settings.interval_min_ms / 1000.0
        hi = self._settings.interval_max_ms / 1000.0
        if lo > hi:
            lo, hi = hi, lo

        # Uniform sample within the configured range
        delay = random.uniform(lo, hi)

        # Optional additional Gaussian variance (% of midpoint)
        if self._settings.variance_pct > 0:
            mid = (lo + hi) / 2.0
            sigma = mid * (self._settings.variance_pct / 100.0) / 2.0
            delay += random.gauss(0.0, sigma)

        # Occasional micro-pause to mimic a human
        if random.random() < _PAUSE_CHANCE:
            delay += random.uniform(0.2, 0.6)

        return max(delay, 0.005)

    def next_jitter(self) -> tuple[int, int]:
        """Return (dx, dy) pixel offset to apply before a click."""
        radius = _JITTER_RADIUS.get(self._settings.jitter, 0)
        if radius == 0:
            return 0, 0
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(0, radius)
        return int(r * math.cos(angle)), int(r * math.sin(angle))
