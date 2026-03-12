"""
gui/main_window.py — Root application window.

Thread-safety notes
───────────────────
• HotkeyListener runs in a pynput background thread. It must NEVER call Qt
  methods directly. We route it through a QMetaObject.invokeMethod so the
  actual work happens in the Qt main thread.
• Clicker callbacks (on_click, on_finished) are called from a daemon thread.
  on_click only writes an int (GIL-safe). on_finished uses invokeMethod.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, QMetaObject, Qt, pyqtSlot
from PyQt6.QtGui import QIcon

from config.settings import Settings
from core.clicker import Clicker
from core.hotkey_listener import HotkeyListener
from gui.settings_panel import SettingsPanel
from gui.status_bar import StatusBar
from gui.region_selector import RegionSelector
from gui.cursor_overlay import AnchorPicker, AnchorOverlay

from pathlib import Path
_ICO = Path(__file__).parent / "icon_autoclicker.ico"
log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("Klikacz — Autoclicker z ludzkim zachowaniem")
        self.setMinimumWidth(480)
        if _ICO.exists():
            self.setWindowIcon(QIcon(str(_ICO)))

        self._settings = settings
        self._anchor_overlay: AnchorOverlay | None = None
        self._pending_clicks: int = 0

        # --- core objects ---
        self._clicker = Clicker(settings)
        # on_click is only used to stash a plain int — GIL-safe, no Qt calls
        self._clicker.on_click = self._on_click_event
        # on_finished is called from worker thread → route to main thread
        self._clicker.on_finished = self._schedule_session_finished

        # Hotkey: pynput thread → route to main thread via invokeMethod
        self._hotkey = HotkeyListener(
            hotkey=settings.hotkey,
            on_toggle=self._schedule_toggle,
        )
        self._hotkey.start()

        # --- GUI ---
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)

        self._panel = SettingsPanel(settings)
        self._status = StatusBar(hotkey=settings.hotkey)

        vbox.addWidget(self._panel)
        vbox.addWidget(self._status)

        # wiring
        self._panel.start_stop_btn.clicked.connect(self._toggle)
        self._panel.settings_changed.connect(self._on_settings_changed)
        self._panel.select_region_requested.connect(self._open_region_selector)
        self._panel.set_anchor_requested.connect(self._open_anchor_picker)
        self._panel.mode_changed.connect(self._on_mode_changed)

        # show overlay if starting in anchor mode with an anchor set
        if settings.click_mode == "anchor_radius" and settings.anchor:
            self._show_anchor_overlay(settings.anchor[0], settings.anchor[1], settings.radius_px)

        # Flush click counter to status bar every 50 ms (main thread only)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._flush_status)
        self._timer.start()

    # ── thread-safe bridges ───────────────────────────────────────────────

    def _schedule_toggle(self) -> None:
        """Called from pynput thread — deferred to Qt main thread."""
        QMetaObject.invokeMethod(self, "_toggle", Qt.ConnectionType.QueuedConnection)

    def _schedule_session_finished(self) -> None:
        """Called from clicker daemon thread — deferred to Qt main thread."""
        QMetaObject.invokeMethod(self, "_on_session_finished",
                                 Qt.ConnectionType.QueuedConnection)

    # ── slots (all run in Qt main thread) ────────────────────────────────

    @pyqtSlot()
    def _toggle(self) -> None:
        try:
            if self._clicker.is_running:
                log.info("Zatrzymywanie klikacza…")
                self._clicker.stop()
                self._panel.set_running(False)
                self._status.update_status("STOPPED", self._pending_clicks)
                # restore anchor overlay if in anchor mode
                s = self._panel.get_settings()
                if s.click_mode == "anchor_radius" and s.anchor:
                    self._show_anchor_overlay(s.anchor[0], s.anchor[1], s.radius_px)
            else:
                s = self._panel.get_settings()
                if s.click_mode == "anchor_radius" and s.anchor is None:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Brak kotwicy",
                                        "Ustaw punkt kotwicy przed uruchomieniem\n"
                                        "(tryb: Kotwica + promień).")
                    return
                log.info("Startowanie klikacza (tryb=%s, min=%d ms, max=%d ms)…",
                         s.click_mode, s.interval_min_ms, s.interval_max_ms)
                self._clicker.update_settings(s)
                self._status.reset()
                self._pending_clicks = 0
                self._hide_anchor_overlay()
                self._clicker.start()
                self._panel.set_running(True)
        except Exception:
            log.exception("Błąd w _toggle")

    def _on_click_event(self, total: int) -> None:
        # Called from worker thread — only stashes a plain int (GIL-safe, no Qt)
        self._pending_clicks = total

    def _flush_status(self) -> None:
        if self._clicker.is_running:
            self._status.update_status("RUNNING", self._pending_clicks)

    @pyqtSlot()
    def _on_session_finished(self) -> None:
        """Always called in the Qt main thread via _schedule_session_finished."""
        self._panel.set_running(False)
        self._status.update_status("STOPPED", self._pending_clicks)

    def _on_settings_changed(self, settings: Settings) -> None:
        self._settings = settings
        self._clicker.update_settings(settings)
        self._hotkey.set_hotkey(settings.hotkey)
        self._status.set_hotkey_label(settings.hotkey)
        # live-update anchor overlay if anchor and radius changed
        if (self._anchor_overlay is not None
                and settings.click_mode == "anchor_radius"
                and settings.anchor):
            self._anchor_overlay.update_anchor(
                settings.anchor[0], settings.anchor[1], settings.radius_px)
        settings.save()

    def _on_mode_changed(self, mode: str) -> None:
        """Show/hide anchor overlay depending on selected mode."""
        if mode == "anchor_radius" and not self._clicker.is_running:
            s = self._panel.get_settings()
            if s.anchor:
                self._show_anchor_overlay(s.anchor[0], s.anchor[1], s.radius_px)
        else:
            self._hide_anchor_overlay()

    # ── overlay helpers ───────────────────────────────────────────────────

    def _show_anchor_overlay(self, cx: int, cy: int, radius: int) -> None:
        if self._anchor_overlay is not None:
            self._anchor_overlay.close()
        self._anchor_overlay = AnchorOverlay(cx, cy, radius)
        self._anchor_overlay.show()

    def _hide_anchor_overlay(self) -> None:
        if self._anchor_overlay is not None:
            self._anchor_overlay.close()
            self._anchor_overlay = None

    # ── anchor picker ─────────────────────────────────────────────────────

    def _open_anchor_picker(self) -> None:
        """Show fullscreen picker — user clicks once to set the anchor point."""
        self._hide_anchor_overlay()
        s = self._panel.get_settings()
        self._picker = AnchorPicker(radius=s.radius_px)
        self._picker.anchor_chosen.connect(self._on_anchor_chosen)
        self._picker.show()
        self._picker.activateWindow()
        self._picker.setFocus()

    def _on_anchor_chosen(self, x: int, y: int) -> None:
        self._panel.set_anchor(x, y)
        s = self._panel.get_settings()
        self._show_anchor_overlay(x, y, s.radius_px)
        log.info("Kotwica ustawiona: (%d, %d), promień=%d px", x, y, s.radius_px)

    # ── region selector ───────────────────────────────────────────────────

    def _open_region_selector(self) -> None:
        """Hide main window, open fullscreen overlay, restore after selection."""
        if self._clicker.is_running:
            self._clicker.stop()
            self._panel.set_running(False)

        self.hide()

        self._selector = RegionSelector()
        self._selector.region_selected.connect(self._on_region_selected)
        self._selector.destroyed.connect(self._on_selector_closed)
        self._selector.show()
        self._selector.activateWindow()

    def _on_region_selected(self, x: int, y: int, w: int, h: int) -> None:
        self._panel.set_region(x, y, w, h)

    def _on_selector_closed(self) -> None:
        self.show()
        self.activateWindow()

    # ── cleanup ───────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._clicker.stop()
        self._hotkey.stop()
        self._hide_anchor_overlay()
        self._settings = self._panel.get_settings()
        self._settings.save()
        super().closeEvent(event)
