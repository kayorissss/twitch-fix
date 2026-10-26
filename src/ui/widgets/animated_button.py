"""Кнопка с собственной отрисовкой, градиентом и плавным hover-свечением."""
from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QPushButton, QSizePolicy

from src.ui.theme import palette


class AnimatedButton(QPushButton):
    """Кнопка с анимированным свечением при наведении.

    Варианты: ``primary`` (фиолетовый градиент), ``secondary`` (контур),
    ``ghost`` (без фона), ``danger`` (красный контур).
    """

    def __init__(
        self,
        text: str = "",
        variant: str = "secondary",
        icon_name: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(text, parent)
        self.variant = variant
        self.icon_name = icon_name
        self._glow = 0.0
        self._pressed = False
        self.setObjectName("animatedButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._font = QFont(self.font())
        self._font.setWeight(QFont.Weight.DemiBold)
        self._animation = QPropertyAnimation(self, b"glow", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def glow(self) -> float:  # type: ignore[override]
        return self._glow

    @glow.setter
    def glow(self, value: float) -> None:
        self._glow = float(value)
        self.update()

    def set_variant(self, variant: str) -> None:
        self.variant = variant
        self.update()

    def _animate_to(self, target: float) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._glow)
        self._animation.setEndValue(target)
        self._animation.start()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._animate_to(0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def sizeHint(self):  # type: ignore[override]
        hint = super().sizeHint()
        return hint.__class__(max(hint.width() + 22, 96), max(hint.height(), 36))

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = palette()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 10.0
        enabled = self.isEnabled()
        accent = QColor(colors.accent)
        hover = QColor(colors.accent_hover)

        # Фон.
        if self.variant == "primary":
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
            gradient.setColorAt(0.0, hover if self._glow > 0.05 else accent)
            gradient.setColorAt(1.0, QColor(colors.accent_dark))
            if not enabled:
                gradient.setColorAt(0.0, QColor(colors.border))
                gradient.setColorAt(1.0, QColor(colors.border))
            p.setPen(Qt.PenStyle.NoPen)
            from PyQt6.QtGui import QBrush  # noqa: PLC0415

            p.setBrush(QBrush(gradient))
            p.drawRoundedRect(rect, radius, radius)
            if self._glow > 0 and enabled:
                glow_pen = QPen(QColor(168, 112, 255, int(110 * self._glow)))
                glow_pen.setWidthF(3.0)
                p.setPen(glow_pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), radius, radius)
        else:
            fill = QColor(colors.surface_alt if self.variant != "ghost" else colors.surface)
            if self.variant == "ghost":
                fill.setAlpha(int(60 * self._glow))
            elif self.variant == "danger":
                fill = QColor(255, 71, 87, 22 + int(40 * self._glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(rect, radius, radius)
            border = QColor(
                colors.error if self.variant == "danger"
                else (accent if self._glow > 0.05 and enabled else colors.border)
            )
            if self.variant != "ghost" or self._glow > 0.05:
                p.setPen(QPen(border, 1.2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        # Текст и иконка.
        text_color = QColor("#ffffff" if self.variant == "primary" else colors.text)
        if not enabled:
            text_color = QColor(colors.text_muted)
        p.setPen(text_color)
        p.setFont(self._font)
        from src.ui.icons import icon_pixmap  # noqa: PLC0415

        usable = rect.adjusted(12, 0, -12, 0)
        if self.icon_name:
            pixmap = icon_pixmap(
                self.icon_name,
                "#ffffff" if self.variant == "primary" else colors.text,
                18,
            )
            p.drawPixmap(
                int(usable.left()), int((rect.height() - 18) / 2), 18, 18, pixmap
            )
            usable = usable.adjusted(25, 0, 0, 0)
        flags = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        # В компактном окне длинный текст аккуратно усекается, а не обрезается.
        metrics = QFontMetrics(self._font)
        label = metrics.elidedText(
            self.text(), Qt.TextElideMode.ElideRight, max(20, int(usable.width()))
        )
        p.drawText(usable, flags, label)
        p.end()
