"""Мини-график доступности Twitch за 24 часа / 7 дней."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from src.ui.theme import palette


class AvailabilityChart(QWidget):
    """Столбчатый график: зелёные/жёлтые/красные бакеты, серые — нет данных."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.values: list[float | None] = []
        self.label = ""
        self.setFixedHeight(86)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_values(self, values: list[float | None], label: str = "") -> None:
        self.values = values
        self.label = label
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = palette()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(colors.surface))
        p.drawRoundedRect(rect, 12, 12)

        # Линии сетки 0/50/100 %.
        grid = QColor(colors.border)
        grid.setAlpha(110)
        p.setPen(QPen(grid, 1, Qt.PenStyle.DashLine))
        for fraction in (0.25, 0.75):
            y = rect.top() + 14 + (rect.height() - 36) * fraction
            p.drawLine(QPointF(rect.left() + 12, y), QPointF(rect.right() - 12, y))

        caption = self.label or ("нет данных" if not any(v is not None for v in self.values) else "")
        if caption:
            p.setPen(QColor(colors.text_muted))
            p.drawText(QRectF(rect.left() + 12, rect.top() + 4, rect.width() - 24, 16),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, caption)

        count = max(1, len(self.values))
        left, right = rect.left() + 12, rect.right() - 12
        top, bottom = rect.top() + 24, rect.bottom() - 10
        slot = (right - left) / count
        bar_width = max(3.0, min(14.0, slot * 0.62))
        for index, value in enumerate(self.values):
            x = left + slot * index + (slot - bar_width) / 2
            if value is None:
                p.setBrush(QColor(colors.border))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(x, bottom - 4, bar_width, 4), 2, 2)
                continue
            height = max(4.0, (bottom - top) * (value / 100.0))
            if value >= 95:
                color = QColor(colors.ok)
            elif value >= 70:
                color = QColor(colors.warn)
            else:
                color = QColor(colors.error)
            gradient = QLinearGradient(x, bottom, x, bottom - height)
            gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 90))
            gradient.setColorAt(1, color)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(gradient))
            p.drawRoundedRect(QRectF(x, bottom - height, bar_width, height), 3, 3)
        p.end()
