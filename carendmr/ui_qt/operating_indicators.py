"""Rein visuelle Betriebsanzeigen für die Qt-Oberfläche.

Die Widgets sind absichtlich nicht fokussierbar und liefern keine eigenen
Accessibility-Texte. Fachliche Zustände werden weiterhin zentral über den
AccessibilityManager gemeldet.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class StatusIndicator(QWidget):
    """Kompakte LED-/Displayanzeige ohne Button-Semantik."""

    _STATES = {
        "disconnected": ("GETRENNT", "#718096"),
        "busy": ("VERBINDET", "#FFD166"),
        "connected": ("EMPFANG", "#59D98E"),
        "tx": ("SENDEN", "#FF6B73"),
        "error": ("FEHLER", "#FF9F43"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = "disconnected"
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(150, 40)
        self.setAccessibleName("")
        self.setAccessibleDescription("")

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        normalized = state if state in self._STATES else "disconnected"
        if normalized != self._state:
            self._state = normalized
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        label, color_name = self._STATES[self._state]
        border = QColor("#4E6278")
        surface = QColor("#101923")
        led = QColor(color_name)

        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(surface)
        painter.drawRoundedRect(rect, 8.0, 8.0)

        center_y = self.height() / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(led)
        painter.drawEllipse(QRectF(14.0, center_y - 5.0, 10.0, 10.0))

        painter.setPen(QColor("#F7FAFC"))
        font = painter.font()
        font.setBold(True)
        # Keine Pixel-Schriftgröße verwenden: QFont meldet bei Pixel-Fonts
        # pointSize() == -1. Einige Qt-Pfade versuchen diesen Wert beim
        # Beenden als Punktgröße zurückzuschreiben und erzeugen dann
        # "QFont::setPointSize: Point size <= 0 (-1)".
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(QRectF(34.0, 0.0, self.width() - 42.0, self.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)


class LevelMeter(QWidget):
    """Audiopegel mit sanftem Rücklauf und kurzem Peak-Hold."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level = 0.0
        self._target = 0.0
        self._peak = 0.0
        self._peak_until = 0.0
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAccessibleName("")
        self.setAccessibleDescription("")
        self.setMinimumHeight(12)
        self.setMaximumHeight(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._animate)
        self._timer.start()

    @property
    def level(self) -> float:
        return self._level

    def set_level(self, value: float) -> None:
        self._target = max(0.0, min(100.0, float(value)))
        if self._target >= self._peak:
            self._peak = self._target
            self._peak_until = time.monotonic() + 0.7
        self.update()

    def reset(self) -> None:
        self._target = 0.0
        self._level = 0.0
        self._peak = 0.0
        self._peak_until = 0.0
        self.update()

    def _animate(self) -> None:
        if self._target >= self._level:
            self._level = self._target
        else:
            self._level = max(self._target, self._level - 5.5)
        if time.monotonic() >= self._peak_until:
            self._peak = max(self._level, self._peak - 3.0)
        if self._target > 0.0:
            self._target = max(0.0, self._target - 2.5)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.setPen(QPen(QColor("#4E6278"), 1.0))
        painter.setBrush(QColor("#263648"))
        painter.drawRoundedRect(rect, 4.0, 4.0)

        fill_width = max(0.0, rect.width() * self._level / 100.0)
        if fill_width > 0:
            fill = QRectF(rect.left(), rect.top(), fill_width, rect.height())
            if self._level >= 90.0:
                color = QColor("#FF6B73")
            elif self._level >= 72.0:
                color = QColor("#FFD166")
            else:
                color = QColor("#59D98E")
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(fill, 4.0, 4.0)

        peak_x = rect.left() + rect.width() * self._peak / 100.0
        if self._peak > 0.0:
            painter.setPen(QPen(QColor("#F7FAFC"), 1.0))
            painter.drawLine(int(peak_x), int(rect.top()), int(peak_x), int(rect.bottom()))
