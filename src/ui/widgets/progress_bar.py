"""Анимированный градиентный прогресс-бар (собственная отрисовка)."""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import QSizePolicy, QWidget

from src.ui.theme import palette


class GradientProgressBar(QWidget):
    """Прогресс 0..100 с плавной анимацией заполнения и свечением."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._value = 0
        self._maximum = 100
        self.setFixedHeight(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._animation = QPropertyAnimation(self, b"value", self)
        self._animation.setDuration(420)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setObjectName("gradientProgress")

    @pyqtProperty(int)
    def value(self) -> int:  # type: ignore[override]
        return self._value

    @value.setter
    def value(self, new_value: int) -> None:
        self._value = max(0, int(new_value))
        self.update()

    def maximum(self) -> int:
        return self._maximum

    def setMaximum(self, maximum: int) -> None:
        self._maximum = max(1, int(maximum))

    def setValue(self, value: int, animate: bool = True) -> None:
        target = int(value)
        if not animate:
            self._animation.stop()
            self.value = target
            return
        self._animation.stop()
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(target)
        self._animation.start()

    def reset(self) -> None:
        self.setValue(0, animate=False)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = palette()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(colors.bg_deep))
        p.drawRoundedRect(rect, 6, 6)

        ratio = min(1.0, max(0.0, self._value / self._maximum))
        if ratio > 0:
            fill = QRectF(rect.left(), rect.top(), max(12.0, rect.width() * ratio), rect.height())
            gradient = QLinearGradient(fill.topLeft(), fill.topRight())
            gradient.setColorAt(0.0, QColor(colors.accent))
            gradient.setColorAt(0.65, QColor("#a970ff"))
            gradient.setColorAt(1.0, QColor("#00d4ff"))
            p.setBrush(QBrush(gradient))
            p.drawRoundedRect(fill, 6, 6)
            # Мягкое свечение на конце заполнения.
            glow = QColor(colors.accent)
            glow.setAlpha(60)
            p.setBrush(glow)
            p.drawRoundedRect(fill.adjusted(0, 2, 0, 4), 6, 6)
        p.end()
