"""
gui/status_bar.py — Bottom status bar widget.

Displays: state (IDLE/RUNNING/STOPPED), total clicks, CPS, active hotkey.
"""

from __future__ import annotations

import time
from collections import deque

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


_STATE_COLORS = {
    "IDLE": "#888888",
    "RUNNING": "#00cc44",
    "STOPPED": "#cc4400",
}


class StatusBar(QWidget):
    def __init__(self, hotkey: str = "F6", parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._click_times: deque[float] = deque()
        self._cps_window = 3.0  # seconds

        # --- widgets ---
        self._state_label = QLabel("IDLE")
        self._clicks_label = QLabel("Kliknięcia: 0")
        self._cps_label = QLabel("CPS: 0.0")
        self._hotkey_label = QLabel(f"Skrót: {hotkey.upper()}")

        for lbl in (self._state_label, self._clicks_label, self._cps_label, self._hotkey_label):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        for w in (self._state_label, self._clicks_label, self._cps_label, self._hotkey_label):
            layout.addWidget(w)

        self._set_state_style("IDLE")

    # --- public API ---

    def update_status(self, state: str, total_clicks: int) -> None:
        self._set_state_style(state)
        self._clicks_label.setText(f"Kliknięcia: {total_clicks}")

        now = time.time()
        if state == "RUNNING":
            self._click_times.append(now)
        # prune old entries
        while self._click_times and (now - self._click_times[0]) > self._cps_window:
            self._click_times.popleft()
        cps = len(self._click_times) / self._cps_window if self._click_times else 0.0
        self._cps_label.setText(f"CPS: {cps:.1f}")

    def reset(self) -> None:
        self._click_times.clear()
        self.update_status("IDLE", 0)

    def set_hotkey_label(self, hotkey: str) -> None:
        self._hotkey_label.setText(f"Skrót: {hotkey.upper()}")

    # --- internal ---

    def _set_state_style(self, state: str) -> None:
        color = _STATE_COLORS.get(state, "#888888")
        self._state_label.setText(state)
        self._state_label.setStyleSheet(
            f"color: {color}; font-weight: bold; padding: 2px 8px;"
        )
