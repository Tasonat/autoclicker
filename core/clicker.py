"""
core/clicker.py — Main clicking engine running in a background thread.
"""

from __future__ import annotations

import time
import threading
import random
import math
import logging
from typing import Callable, Optional

from pynput.mouse import Button, Controller as MouseController

from config.settings import Settings
from core.humanizer import Humanizer

log = logging.getLogger(__name__)


def _screen_bounds() -> tuple[int, int, int, int]:
    """Return (min_x, min_y, max_x, max_y) spanning all monitors."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        # Virtual screen covers all monitors
        x = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
        w = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
        h = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
        return x, y, x + w - 1, y + h - 1
    except Exception:
        return 0, 0, 7680, 4320  # safe fallback


class Clicker:
    """Perform mouse clicks with humanised timing in a daemon thread."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._humanizer = Humanizer(settings)
        self._mouse = MouseController()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._total_clicks = 0

        # External callbacks (set by GUI / owner)
        self.on_click: Optional[Callable[[int], None]] = None
        self.on_finished: Optional[Callable[[], None]] = None

    # --- settings hot-reload ---
    def update_settings(self, settings: Settings) -> None:
        self._settings = settings
        self._humanizer.update_settings(settings)

    # --- control ---
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._total_clicks = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # --- internal loop ---
    def _loop(self) -> None:
        log.info("Pętla klikania startuje (tryb=%s, przycisk=%s, cel=%d)",
                 self._settings.click_mode, self._settings.mouse_button,
                 self._settings.click_count)
        try:
            self._loop_body()
        except Exception:
            log.exception("Nieoczekiwany błąd w pętli klikania — zatrzymuję")
            self._running = False
        finally:
            if self.on_finished:
                self.on_finished()
            log.info("Pętla klikania zakończona. Łącznie kliknięć: %d", self._total_clicks)

    def _loop_body(self) -> None:
        button = Button.left if self._settings.mouse_button == "left" else Button.right
        target = self._settings.click_count  # 0 = infinite
        sx_min, sy_min, sx_max, sy_max = _screen_bounds()

        while self._running:
            try:
                mode = self._settings.click_mode

                if mode == "region" and self._settings.region:
                    rx, ry, rw, rh = self._settings.region
                    cx = rx + random.randint(0, max(rw - 1, 0))
                    cy = ry + random.randint(0, max(rh - 1, 0))
                    dx, dy = self._humanizer.next_jitter()
                    new_x = max(sx_min, min(sx_max, cx + dx))
                    new_y = max(sy_min, min(sy_max, cy + dy))
                    log.debug("region click → (%d, %d)", new_x, new_y)
                    self._mouse.position = (new_x, new_y)

                elif mode == "anchor_radius" and self._settings.anchor:
                    anc_x, anc_y = self._settings.anchor
                    r = self._settings.radius_px
                    angle = random.uniform(0, 2 * math.pi)
                    dist  = random.uniform(0, r)
                    dx, dy = self._humanizer.next_jitter()
                    new_x = max(sx_min, min(sx_max, int(anc_x + dist * math.cos(angle)) + dx))
                    new_y = max(sy_min, min(sy_max, int(anc_y + dist * math.sin(angle)) + dy))
                    log.debug("anchor_radius click (%d px) @ (%d,%d) → (%d, %d)",
                              r, anc_x, anc_y, new_x, new_y)
                    self._mouse.position = (new_x, new_y)

                else:  # "cursor"
                    dx, dy = self._humanizer.next_jitter()
                    if dx or dy:
                        self._mouse.move(dx, dy)

                self._mouse.click(button)
                self._total_clicks += 1

                if self.on_click:
                    self.on_click(self._total_clicks)

                if target > 0 and self._total_clicks >= target:
                    log.info("Osiągnięto cel %d kliknięć.", target)
                    self._running = False
                    break

            except Exception:
                log.exception("Błąd podczas pojedynczego kliknięcia (klik #%d) — kontynuuję",
                              self._total_clicks)
                # don't crash the whole loop on a single bad click
                time.sleep(0.05)

            # humanised delay
            delay = self._humanizer.next_delay()
            end = time.perf_counter() + delay
            while self._running and time.perf_counter() < end:
                time.sleep(0.01)
