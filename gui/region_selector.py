"""
gui/region_selector.py — Fullscreen transparent overlay for selecting a click region.

User clicks and drags to define a rectangle. When mouse is released the selected
QRect is returned via the ``region_selected`` signal (x, y, w, h).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QApplication, QLabel
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


class RegionSelector(QWidget):
    """
    Pełnoekranowa przezroczysta nakładka.
    Użytkownik rysuje prostokąt — po puszczeniu myszy emituje ``region_selected(x, y, w, h)``.
    """

    region_selected = pyqtSignal(int, int, int, int)  # x, y, w, h

    def __init__(self) -> None:
        super().__init__()

        # Span across all screens
        total = QRect()
        for screen in QApplication.screens():
            total = total.united(screen.geometry())

        self.setGeometry(total)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._confirmed = False

        # Instruction label
        self._hint = QLabel("Kliknij i przeciągnij, aby zaznaczyć obszar klikania\n"
                            "[ ESC ] — anuluj", self)
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet(
            "color: white; background: rgba(0,0,0,160); "
            "padding: 8px 16px; border-radius: 6px; font-size: 13px;"
        )
        self._hint.adjustSize()
        self._hint.move(
            (total.width() - self._hint.width()) // 2,
            total.height() // 2 - self._hint.height() // 2
        )

    # --- Qt events ---

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self._hint.hide()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._origin:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._origin:
            rect = self._selection_rect()
            if rect.width() > 5 and rect.height() > 5:
                # Convert from widget-local to global (virtual desktop) coords
                global_origin = self.mapToGlobal(rect.topLeft())
                self._confirmed = True
                self.region_selected.emit(
                    global_origin.x(), global_origin.y(),
                    rect.width(), rect.height()
                )
            self.close()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)

        # dim whole screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

        if self._origin and self._current:
            sel = self._selection_rect()

            # cut-out (clear) the selected region so it looks bright
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(sel, QColor(0, 0, 0, 255))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # border
            pen = QPen(QColor(0, 200, 255), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(sel)

            # size label
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 10))
            label = f"{sel.width()} × {sel.height()} px"
            painter.drawText(sel.left() + 4, sel.top() - 6, label)

        painter.end()

    # --- helpers ---

    def _selection_rect(self) -> QRect:
        return QRect(self._origin, self._current).normalized()
