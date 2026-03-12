"""
gui/settings_panel.py — Settings form widget.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QSlider, QComboBox,
    QCheckBox, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QButtonGroup, QRadioButton, QGroupBox, QVBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal

from config.settings import Settings


# ---------- helpers: ms <-> (h, m, s, ms) ----------

def ms_to_parts(total_ms: int) -> tuple[int, int, int, int]:
    h  = total_ms // 3_600_000
    total_ms -= h * 3_600_000
    m  = total_ms // 60_000
    total_ms -= m * 60_000
    s  = total_ms // 1_000
    ms = total_ms - s * 1_000
    return h, m, s, ms


def parts_to_ms(h: int, m: int, s: int, ms: int) -> int:
    return h * 3_600_000 + m * 60_000 + s * 1_000 + ms


def _spin(lo, hi, val, suffix, width=72) -> QSpinBox:
    sp = QSpinBox()
    sp.setRange(lo, hi)
    sp.setValue(val)
    sp.setSuffix(suffix)
    sp.setMinimumWidth(width)
    return sp


def _hrow(widgets) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(4)
    for w in widgets:
        row.addWidget(w)
    return row


class SettingsPanel(QWidget):
    """Editable form that exposes all ``Settings`` fields."""

    settings_changed        = pyqtSignal(object)  # emits Settings
    select_region_requested = pyqtSignal()
    set_anchor_requested    = pyqtSignal()         # "Ustaw kotwicę" button
    mode_changed            = pyqtSignal(str)      # "cursor"|"anchor_radius"|"region"

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._building = True
        self._region   = settings.region
        self._anchor   = settings.anchor

        form = QFormLayout(self)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # ── 1. TRYB KLIKANIA ──────────────────────────────────────────────
        mode_box    = QGroupBox("Tryb klikania")
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setSpacing(4)

        self._mode_group = QButtonGroup(self)
        self._rb_cursor = QRadioButton("Tam gdzie jest kursor")
        self._rb_radius = QRadioButton("Kotwica + promień:")
        self._rb_region = QRadioButton("Wyznaczony obszar ekranu")
        for rb in (self._rb_cursor, self._rb_radius, self._rb_region):
            self._mode_group.addButton(rb)
            mode_layout.addWidget(rb)

        # anchor+radius row
        radius_inner = QHBoxLayout()
        radius_inner.setContentsMargins(22, 0, 0, 0)
        self._radius_spin = _spin(5, 2000, settings.radius_px, " px", 90)
        self._radius_spin.valueChanged.connect(self._emit)
        self._anchor_btn = QPushButton("📌  Ustaw kotwicę")
        self._anchor_btn.clicked.connect(self.set_anchor_requested)
        radius_inner.addWidget(self._radius_spin)
        radius_inner.addWidget(self._anchor_btn)
        radius_inner.addStretch()
        mode_layout.addLayout(radius_inner)

        self._anchor_label = QLabel(self._anchor_text(settings.anchor))
        self._anchor_label.setContentsMargins(22, 0, 0, 4)
        self._anchor_label.setStyleSheet("color:#555; font-size:11px;")
        mode_layout.addWidget(self._anchor_label)

        # region row
        region_inner = QHBoxLayout()
        region_inner.setContentsMargins(22, 0, 0, 0)
        self._region_btn       = QPushButton("🖱  Zaznacz obszar")
        self._region_clear_btn = QPushButton("✕")
        self._region_clear_btn.setMaximumWidth(28)
        self._region_clear_btn.setToolTip("Usuń obszar")
        self._region_btn.clicked.connect(self.select_region_requested)
        self._region_clear_btn.clicked.connect(self._clear_region)
        region_inner.addWidget(self._region_btn)
        region_inner.addWidget(self._region_clear_btn)
        region_inner.addStretch()
        mode_layout.addLayout(region_inner)

        self._region_label = QLabel(self._region_text(settings.region))
        self._region_label.setContentsMargins(22, 0, 0, 0)
        self._region_label.setStyleSheet("color:#555; font-size:11px;")
        mode_layout.addWidget(self._region_label)

        form.addRow(mode_box)

        _mode_map = {"cursor": self._rb_cursor,
                     "anchor_radius": self._rb_radius,
                     "region": self._rb_region}
        _mode_map.get(settings.click_mode, self._rb_cursor).setChecked(True)
        self._apply_mode_visibility(settings.click_mode)
        self._mode_group.buttonToggled.connect(self._on_mode_toggled)

        # ── 2. INTERWAŁ kliknięć ─────────────────────────────────────────
        interval_box = QGroupBox("Interwał kliknięć")
        ib = QFormLayout(interval_box)
        ib.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        h0, m0, s0, ms0 = ms_to_parts(settings.interval_min_ms)
        self._min_h  = _spin(0, 23,  h0,  " godz", 80)
        self._min_m  = _spin(0, 59,  m0,  " min")
        self._min_s  = _spin(0, 59,  s0,  " sek")
        self._min_ms = _spin(0, 999, ms0, " ms")
        for sp in (self._min_h, self._min_m, self._min_s, self._min_ms):
            sp.valueChanged.connect(self._on_interval_changed)
        ib.addRow("Od:", _hrow([self._min_h, self._min_m, self._min_s, self._min_ms]))

        h1, m1, s1, ms1 = ms_to_parts(settings.interval_max_ms)
        self._max_h  = _spin(0, 23,  h1,  " godz", 80)
        self._max_m  = _spin(0, 59,  m1,  " min")
        self._max_s  = _spin(0, 59,  s1,  " sek")
        self._max_ms = _spin(0, 999, ms1, " ms")
        for sp in (self._max_h, self._max_m, self._max_s, self._max_ms):
            sp.valueChanged.connect(self._on_interval_changed)
        ib.addRow("Do:", _hrow([self._max_h, self._max_m, self._max_s, self._max_ms]))

        self._interval_label = QLabel()
        self._interval_label.setStyleSheet("color:#555; font-size:11px;")
        self._update_interval_label()
        ib.addRow("", self._interval_label)
        form.addRow(interval_box)

        # ── 3. DODATKOWA LOSOWOŚĆ (gaussian variance) ─────────────────────
        variance_row = QHBoxLayout()
        self._variance_slider  = QSlider(Qt.Orientation.Horizontal)
        self._variance_slider.setRange(0, 80)
        self._variance_slider.setValue(settings.variance_pct)
        self._variance_val_lbl = QLabel(f"{settings.variance_pct} %")
        self._variance_slider.valueChanged.connect(self._on_variance)
        variance_row.addWidget(self._variance_slider)
        variance_row.addWidget(self._variance_val_lbl)
        form.addRow("Dod. losowość (σ):", variance_row)

        # ── 4. PRZYCISK MYSZY ─────────────────────────────────────────────
        self._button_combo = QComboBox()
        self._button_combo.addItems(["left", "right"])
        self._button_combo.setCurrentText(settings.mouse_button)
        self._button_combo.currentTextChanged.connect(self._emit)
        form.addRow("Przycisk myszy:", self._button_combo)

        # ── 5. JITTER ─────────────────────────────────────────────────────
        self._jitter_combo = QComboBox()
        self._jitter_combo.addItems(["none", "low", "medium"])
        self._jitter_combo.setCurrentText(settings.jitter)
        self._jitter_combo.currentTextChanged.connect(self._emit)
        form.addRow("Jitter (drgania):", self._jitter_combo)

        # ── 6. LICZBA KLIKNIĘĆ ────────────────────────────────────────────
        count_row = QHBoxLayout()
        self._infinite_check = QCheckBox("Nieskończone")
        self._infinite_check.setChecked(settings.click_count == 0)
        self._count_spin = _spin(1, 10_000_000, max(settings.click_count, 1), "")
        self._count_spin.setEnabled(settings.click_count != 0)
        self._infinite_check.toggled.connect(self._on_infinite_toggle)
        self._count_spin.valueChanged.connect(self._emit)
        count_row.addWidget(self._infinite_check)
        count_row.addWidget(self._count_spin)
        form.addRow("Liczba kliknięć:", count_row)

        # ── 7. SKRÓT KLAWISZOWY ───────────────────────────────────────────
        hotkey_row = QHBoxLayout()
        self._hotkey_display = QLineEdit(settings.hotkey.upper())
        self._hotkey_display.setReadOnly(True)
        self._hotkey_display.setMaximumWidth(80)
        self._hotkey_btn = QPushButton("Zmień…")
        self._hotkey_btn.clicked.connect(self._capture_hotkey)
        hotkey_row.addWidget(self._hotkey_display)
        hotkey_row.addWidget(self._hotkey_btn)
        form.addRow("Skrót klawiszowy:", hotkey_row)

        # ── 8. SKRÓT NA PULPICIE ──────────────────────────────────────────
        self._shortcut_btn = QPushButton("�  Utwórz skrót na pulpicie")
        self._shortcut_btn.clicked.connect(self._create_desktop_shortcut)
        form.addRow(self._shortcut_btn)

        # ── 9. START / STOP ───────────────────────────────────────────────
        self.start_stop_btn = QPushButton("▶  Start")
        self.start_stop_btn.setMinimumHeight(40)
        self.start_stop_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        form.addRow(self.start_stop_btn)

        self._building = False

    # ── public helpers ────────────────────────────────────────────────────

    def get_settings(self) -> Settings:
        lo = parts_to_ms(self._min_h.value(), self._min_m.value(),
                         self._min_s.value(), self._min_ms.value())
        hi = parts_to_ms(self._max_h.value(), self._max_m.value(),
                         self._max_s.value(), self._max_ms.value())
        if lo > hi:
            lo, hi = hi, lo
        return Settings(
            interval_ms=lo,
            interval_min_ms=lo,
            interval_max_ms=hi,
            variance_pct=self._variance_slider.value(),
            mouse_button=self._button_combo.currentText(),
            jitter=self._jitter_combo.currentText(),
            click_count=0 if self._infinite_check.isChecked() else self._count_spin.value(),
            hotkey=self._hotkey_display.text().lower(),
            click_mode=self._current_mode(),
            radius_px=self._radius_spin.value(),
            anchor=self._anchor,
            region=self._region,
        )

    def set_hotkey_text(self, text: str) -> None:
        self._hotkey_display.setText(text.upper())

    def set_running(self, running: bool) -> None:
        self.start_stop_btn.setText("⏹  Stop" if running else "▶  Start")

    def set_region(self, x: int, y: int, w: int, h: int) -> None:
        self._region = (x, y, w, h)
        self._region_label.setText(self._region_text(self._region))
        self._emit()

    def set_anchor(self, x: int, y: int) -> None:
        self._anchor = (x, y)
        self._anchor_label.setText(self._anchor_text(self._anchor))
        self._emit()

    # ── internal helpers ──────────────────────────────────────────────────

    def _current_mode(self) -> str:
        if self._rb_radius.isChecked():
            return "anchor_radius"
        if self._rb_region.isChecked():
            return "region"
        return "cursor"

    def _apply_mode_visibility(self, mode: str) -> None:
        is_anchor = mode == "anchor_radius"
        is_region = mode == "region"
        self._radius_spin.setVisible(is_anchor)
        self._anchor_btn.setVisible(is_anchor)
        self._anchor_label.setVisible(is_anchor)
        self._region_btn.setVisible(is_region)
        self._region_clear_btn.setVisible(is_region)
        self._region_label.setVisible(is_region)

    def _clear_region(self) -> None:
        self._region = None
        self._region_label.setText(self._region_text(None))
        self._emit()

    @staticmethod
    def _region_text(region) -> str:
        if region is None:
            return "brak obszaru"
        x, y, w, h = region
        return f"x={x}, y={y},  {w} × {h} px"

    @staticmethod
    def _anchor_text(anchor) -> str:
        if anchor is None:
            return "⚠  Brak kotwicy — kliknij 'Ustaw kotwicę'"
        x, y = anchor
        return f"📌  Kotwica: x={x}, y={y}"

    def _create_desktop_shortcut(self) -> None:
        import sys
        from pathlib import Path
        from PyQt6.QtWidgets import QMessageBox
        try:
            try:
                import winshell  # type: ignore
            except ImportError:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip",
                                       "install", "winshell", "pywin32", "-q"])
                import winshell  # type: ignore

            desktop  = Path(winshell.desktop())
            bat_path = Path(__file__).resolve().parent.parent / "run.bat"
            ico_path = Path(__file__).resolve().parent / "icon_autoclicker.ico"
            lnk_path = desktop / "Klikacz.lnk"

            with winshell.shortcut(str(lnk_path)) as sc:
                sc.path               = str(bat_path)
                sc.working_directory  = str(bat_path.parent)
                sc.description        = "Klikacz — autoclicker z ludzkim zachowaniem"
                if ico_path.exists():
                    sc.icon_location  = (str(ico_path), 0)

            QMessageBox.information(self, "Skrót utworzony",
                                    f"Skrót 'Klikacz' został dodany na pulpit:\n{lnk_path}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się utworzyć skrótu:\n{e}")

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_mode_toggled(self, btn, checked: bool) -> None:
        if not checked:
            return
        mode = self._current_mode()
        self._apply_mode_visibility(mode)
        self.mode_changed.emit(mode)
        self._emit()

    def _on_interval_changed(self) -> None:
        self._update_interval_label()
        self._emit()

    def _update_interval_label(self) -> None:
        lo = parts_to_ms(self._min_h.value(), self._min_m.value(),
                         self._min_s.value(), self._min_ms.value())
        hi = parts_to_ms(self._max_h.value(), self._max_m.value(),
                         self._max_s.value(), self._max_ms.value())
        if lo == 0 and hi == 0:
            self._interval_label.setText("⚠  Ustaw przynajmniej 1 ms")
            self._interval_label.setStyleSheet("color:#cc4400; font-size:11px;")
        elif lo > hi:
            self._interval_label.setText("⚠  Wartość 'Od' jest większa niż 'Do'")
            self._interval_label.setStyleSheet("color:#cc4400; font-size:11px;")
        else:
            self._interval_label.setText(
                f"Losowy czas: {lo:,} – {hi:,} ms  ({lo/1000:.3f} – {hi/1000:.3f} s)"
            )
            self._interval_label.setStyleSheet("color:#555; font-size:11px;")

    def _emit(self) -> None:
        if not self._building:
            self.settings_changed.emit(self.get_settings())

    def _on_variance(self, val: int) -> None:
        self._variance_val_lbl.setText(f"{val} %")
        self._emit()

    def _on_infinite_toggle(self, checked: bool) -> None:
        self._count_spin.setEnabled(not checked)
        self._emit()

    def _capture_hotkey(self) -> None:
        self._hotkey_btn.setText("Naciśnij klawisz…")
        self._hotkey_btn.setEnabled(False)
        self._hotkey_display.setFocus()
        self._hotkey_display.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        from PyQt6.QtCore import QEvent
        if obj is self._hotkey_display and event.type() == QEvent.Type.KeyPress:
            from PyQt6.QtCore import Qt as _Qt
            key_enum = _Qt.Key(event.key())
            name = key_enum.name.decode() if isinstance(key_enum.name, bytes) else key_enum.name
            if name.startswith("Key_"):
                name = name[4:]
            self._hotkey_display.setText(name.upper())
            self._hotkey_display.removeEventFilter(self)
            self._hotkey_btn.setText("Zmień…")
            self._hotkey_btn.setEnabled(True)
            self._emit()
            return True
        return super().eventFilter(obj, event)
