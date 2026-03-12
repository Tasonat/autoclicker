"""
config/settings.py — Settings dataclass + persistence (JSON).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Tuple

_DEFAULT_PATH = Path(__file__).with_name("settings.json")


@dataclass
class Settings:
    # --- timing ---
    interval_ms: int = 100            # base click interval (used when min==max or legacy)
    interval_min_ms: int = 80         # random range lower bound
    interval_max_ms: int = 120        # random range upper bound
    variance_pct: int = 0             # extra gaussian variance on top of range (0 = off)

    # --- behaviour ---
    mouse_button: str = "left"        # "left" or "right"
    jitter: str = "low"               # "none" | "low" | "medium"
    click_count: int = 0              # 0 = infinite, N = stop after N clicks
    hotkey: str = "f6"                # e.g. "f6"

    # --- click mode ---
    # "cursor"        — click exactly where cursor is (+ jitter)
    # "anchor_radius" — random point within radius_px around a fixed anchor point
    # "region"        — random point inside fixed region rectangle
    click_mode: str = "cursor"
    radius_px: int = 50               # used when click_mode == "anchor_radius"

    # fixed anchor point for anchor_radius mode: (x, y) in screen pixels
    anchor: Optional[Tuple[int, int]] = None

    # click region: (x, y, width, height) in screen pixels
    region: Optional[Tuple[int, int, int, int]] = None

    # --- persistence helpers ---
    @staticmethod
    def load(path: str | Path | None = None) -> Settings:
        path = Path(path) if path else _DEFAULT_PATH
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                filtered = {k: v for k, v in data.items() if k in Settings.__dataclass_fields__}
                # JSON stores tuples as lists — convert region and anchor back
                if "region" in filtered and filtered["region"] is not None:
                    filtered["region"] = tuple(filtered["region"])
                if "anchor" in filtered and filtered["anchor"] is not None:
                    filtered["anchor"] = tuple(filtered["anchor"])
                # Legacy: if only interval_ms present, seed min/max from it
                if "interval_ms" in filtered and "interval_min_ms" not in filtered:
                    ms = filtered["interval_ms"]
                    filtered.setdefault("interval_min_ms", ms)
                    filtered.setdefault("interval_max_ms", ms)
                return Settings(**filtered)
            except Exception:
                pass
        return Settings()

    def save(self, path: str | Path | None = None) -> None:
        path = Path(path) if path else _DEFAULT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
