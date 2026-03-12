"""
gui/cursor_overlay.py — Anchor-radius click-mode helpers.

AnchorPicker
    Full-screen overlay. Tracks cursor and draws a live radius preview.
    User clicks once → emits anchor_chosen(x, y) and closes.
    Escape → cancels.

AnchorOverlay
    Always-on-top window showing the fixed anchor + radius circle after
    the point has been set. Uses WS_EX_TRANSPARENT via ctypes so that
    mouse events physically pass through the window to whatever is below.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QCursor, QFont


# ── helpers ───────────────────────────────────────────────────────────────────

def _set_click_through(hwnd: int) -> None:
    """Apply WS_EX_TRANSPARENT | WS_EX_LAYERED via WinAPI so all mouse events
    pass through the window regardless of Qt attributes."""
    GWL_EXSTYLE      = -20
    WS_EX_LAYERED    = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    user32 = ctypes.windll.user32
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                          style | WS_EX_LAYERED | WS_EX_TRANSPARENT)


# ── AnchorPicker ──────────────────────────────────────────────────────────────

class AnchorPicker(QWidget):
    """
    Full-screen semi-transparent overlay with a live radius preview.
    One left-click → records position → emits anchor_chosen → closes.
    Escape → cancels.
    """

    anchor_chosen = pyqtSignal(int, int)   # x, y in screen pixels

    def __init__(self, radius: int = 50) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self._radius   = radius
        self._cursor_local = QPoint(0, 0)   # in widget-local coords

        # span all monitors
        total = QRect()
        for screen in QApplication.screens():
            total = total.united(screen.geometry())
        self.setGeometry(total)

    def set_radius(self, r: int) -> None:
        self._radius = r

    # ── events ────────────────────────────────────────────────────────────

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        self._cursor_local = event.position().toPoint()
        self.update()   # repaint with new cursor position

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()
            self.anchor_chosen.emit(pos.x(), pos.y())
            self.close()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # dark tint to signal active overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 50))

        cx = self._cursor_local.x()
        cy = self._cursor_local.y()
        r  = self._radius

        # radius fill
        painter.setBrush(QBrush(QColor(255, 140, 0, 45)))
        pen = QPen(QColor(255, 160, 0, 220), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # crosshair
        arm = min(14, r)
        painter.setPen(QPen(QColor(255, 200, 0, 230), 1))
        painter.drawLine(cx - arm, cy, cx + arm, cy)
        painter.drawLine(cx, cy - arm, cx, cy + arm)

        # centre dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 160, 0, 240)))
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)

        # instruction text
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 220))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "\n\nKliknij żeby ustawić kotwicę    [Esc] — anuluj",
        )

        painter.end()


# ── AnchorOverlay ─────────────────────────────────────────────────────────────

class AnchorOverlay(QWidget):
    """
    Always-on-top window showing the anchor point + radius circle.
    Mouse events physically pass through (WS_EX_TRANSPARENT via WinAPI),
    so anything underneath remains fully clickable.
    """

    _PAD = 12  # padding around the radius circle in pixels

    def __init__(self, cx: int, cy: int, radius: int) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._radius = radius
        self._cx = cx
        self._cy = cy
        self._reposition()
        self._apply_click_through()

    def update_anchor(self, cx: int, cy: int, radius: int) -> None:
        self._cx     = cx
        self._cy     = cy
        self._radius = radius
        self._reposition()
        self._apply_click_through()
        self.update()

    # ── internal ──────────────────────────────────────────────────────────

    def _reposition(self) -> None:
        half = self._radius + self._PAD
        self.resize(half * 2, half * 2)
        self.move(self._cx - half, self._cy - half)

    def _apply_click_through(self) -> None:
        """Set WS_EX_TRANSPARENT after the window handle exists."""
        hwnd = self.winId()
        if hwnd:
            _set_click_through(int(hwnd))

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        # winId() is guaranteed valid after show
        self._apply_click_through()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        half = self.width() // 2
        r    = self._radius

        # filled circle
        painter.setBrush(QBrush(QColor(255, 120, 0, 30)))
        pen = QPen(QColor(255, 150, 0, 210), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(half - r, half - r, r * 2, r * 2)

        # crosshair arms
        arm = min(12, r)
        painter.setPen(QPen(QColor(255, 150, 0, 210), 1))
        painter.drawLine(half - arm, half, half + arm, half)
        painter.drawLine(half, half - arm, half, half + arm)

        # centre dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 150, 0, 230)))
        painter.drawEllipse(half - 4, half - 4, 8, 8)

        painter.end()


