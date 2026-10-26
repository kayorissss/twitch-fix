"""Карточки статуса: пульсирующий индикатор + кликабельная мини-карточка."""
from __future__ import annotations

import math
import time

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.config.i18n import i18n
from src.ui.icons import icon_pixmap
from src.ui.theme import palette, status_color


class PulsingDot(QWidget):
    """Пульсирующий светящийся индикатор (анимация на QTimer)."""

    def __init__(self, size: int = 14, color: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._color = color or palette().ok
        self._active = True
        self.setFixedSize(size * 3, size * 3)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(45)
        self._start = time.monotonic()

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() / 2, self.height() / 2
        color = QColor(self._color)
        if self._active:
            phase = (time.monotonic() - self._start) * 1.8
            wave = 0.5 + 0.5 * math.sin(phase)
            halo = QColor(color)
            halo.setAlpha(int(35 + 65 * wave))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            radius = self._size * (0.9 + 0.4 * wave)
            p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        r = self._size * 0.42
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        p.end()


class StatusCard(QFrame):
    """Мини-карточка быстрого статуса (или большая hero-карточка)."""

    clicked = pyqtSignal(str)

    def __init__(
        self,
        check_id: str,
        title: str,
        icon_name: str = "info",
        kind: str = "mini",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.check_id = check_id
        self.icon_name = icon_name
        self.kind = kind
        self.status = "info"
        self.setObjectName("heroCard" if kind == "hero" else "statusCard")
        self.setProperty("card", "true")
        self.setProperty("cardHover", "true")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(26, 26)
        self.dot = PulsingDot(size=10 if kind == "hero" else 7, color=palette().text_muted)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle" if kind == "mini" else "heroTitle")
        self.status_label = QLabel(i18n.tr("common.not_checked"))
        self.status_label.setObjectName("cardStatus")
        if kind == "mini":
            # Текст статуса не должен раздувать карточку: он усекается,
            # а размер подсказки игнорируется layout'ом.
            self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            self.status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("heroHint")
        self.hint_label.setWordWrap(True)
        self.hint_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.hint_label.setVisible(kind == "hero")

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        if kind == "mini":
            header.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignLeft)
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            text_layout.addWidget(self.title_label)
            text_layout.addWidget(self.status_label)
            header.addLayout(text_layout, 1)
            header.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignRight)
        else:
            header.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
            text_layout = QVBoxLayout()
            text_layout.setSpacing(4)
            text_layout.addWidget(self.title_label)
            text_layout.addWidget(self.status_label)
            text_layout.addWidget(self.hint_label)
            header.addLayout(text_layout, 1)
            header.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignRight)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18 if kind == "hero" else 14, 14, 18 if kind == "hero" else 14, 14)
        outer.addLayout(header)
        self.refresh_icon()

    def refresh_icon(self) -> None:
        colors = palette()
        size = 26 if self.kind == "hero" else 22
        self.icon_label.setPixmap(icon_pixmap(self.icon_name, colors.accent, size))

    def set_status(self, status: str, text: str, hint: str = "") -> None:
        self.status = status
        display = text or i18n.tr("common.not_checked")
        if self.kind == "mini" and len(display) > 42:
            # Длинные тексты не должны раздувать сетку 2x3.
            display = display[:40].rstrip() + "…"
        self.status_label.setText(display)
        color = status_color(status)
        self.status_label.setStyleSheet(f"color: {color};")
        self.dot.set_color(color)
        self.dot.set_active(status == "ok" or status == "running")
        self.hint_label.setText(hint)
        self.setProperty("status", status)
        self.style().polish(self)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.check_id)
        super().mousePressEvent(event)
