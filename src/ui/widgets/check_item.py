"""Карточка одной проверки: спиннер → галочка/крестик + раскрываемые детали."""
from __future__ import annotations

import time

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config.i18n import i18n
from src.core.diagnostics.base_check import CheckResult
from src.ui.theme import status_color


class StatusGlyph(QWidget):
    """Кружок со статусом: чек / крест / треугольник / вращающийся спиннер."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.state = "running"
        self.setFixedSize(28, 28)
        self.spinner = QTimer(self)
        self.spinner.timeout.connect(self.update)
        self.spinner.start(40)
        self._start = time.monotonic()

    def set_state(self, state: str) -> None:
        self.state = state
        if state == "running":
            self.spinner.start(40)
        else:
            self.spinner.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        color = QColor(status_color(self.state))
        p.setPen(Qt.PenStyle.NoPen)
        background = QColor(color)
        background.setAlpha(38)
        p.setBrush(background)
        p.drawEllipse(rect)
        pen = QPen(color)
        pen.setWidthF(2.1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2

        if self.state == "running":
            angle = (time.monotonic() - self._start) * 320
            p.save()
            p.translate(cx, cy)
            p.rotate(angle)
            p.drawArc(QRectF(-7, -7, 14, 14), 0, 270 * 16)
            p.restore()
        elif self.state in ("ok", "info"):
            p.drawLine(int(cx - 5), int(cy), int(cx - 1), int(cy + 4))
            p.drawLine(int(cx - 1), int(cy + 4), int(cx + 6), int(cy - 5))
        elif self.state == "error":
            p.drawLine(int(cx - 4), int(cy - 4), int(cx + 4), int(cy + 4))
            p.drawLine(int(cx + 4), int(cy - 4), int(cx - 4), int(cy + 4))
        elif self.state == "warning":
            p.drawLine(int(cx), int(cy - 6), int(cx + 6), int(cy + 5))
            p.drawLine(int(cx + 6), int(cy + 5), int(cx - 6), int(cy + 5))
            p.drawLine(int(cx - 6), int(cy + 5), int(cx), int(cy - 6))
            p.drawLine(int(cx), int(cy - 2), int(cx), int(cy + 1))
        else:  # skipped
            p.drawLine(int(cx - 5), int(cy), int(cx + 5), int(cy))
        p.end()


class CheckItem(QFrame):
    """Карточка проверки с fade-in анимацией и раскрытием деталей."""

    toggled = pyqtSignal(str)

    def __init__(self, result: CheckResult, parent=None) -> None:
        super().__init__(parent)
        self.result = result
        self.setObjectName("checkItem")
        self.setProperty("card", "true")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.glyph = StatusGlyph()
        self.glyph.set_state(result.status.value)
        self.title_label = QLabel(result.title_for(i18n.language))
        self.title_label.setObjectName("cardTitle")
        self.summary_label = QLabel(result.summary_for(i18n.language) or i18n.tr("common.running"))
        self.summary_label.setObjectName("muted")
        self.summary_label.setWordWrap(True)
        self.duration_label = QLabel("")
        self.duration_label.setObjectName("muted")
        self.duration_label.setFixedWidth(70)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.expand_button = QPushButton("⌄")
        self.expand_button.setObjectName("ghostButton")
        self.expand_button.setFixedSize(28, 28)
        self.expand_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_button.clicked.connect(self.toggle_details)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        header.addWidget(self.glyph, 0, Qt.AlignmentFlag.AlignVCenter)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.summary_label)
        header.addLayout(text_layout, 1)
        header.addWidget(self.duration_label, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.expand_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setObjectName("checkDetails")
        self.details.setPlainText("\n".join(result.details) if result.details else "-")
        self.details.setFixedHeight(0)
        self.details.setVisible(False)
        self.details.setStyleSheet("background: transparent; border: none; padding: 6px 0 0 38px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(6)
        outer.addLayout(header)
        outer.addWidget(self.details)
        self.expanded = False
        self.fade_in()

    def fade_in(self) -> None:
        """Плавное появление. Эффект удаляется сразу после анимации:

        постоянный QGraphicsEffect на элементе внутри layout может
        сдвинуть содержимое при отрисовке.
        """
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        opacity = QPropertyAnimation(effect, b"opacity", self)
        opacity.setDuration(300)
        opacity.setStartValue(0.0)
        opacity.setEndValue(1.0)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        opacity.finished.connect(lambda: self.setGraphicsEffect(None))
        setattr(self, "_fade_animation", opacity)
        opacity.start()

    def set_result(self, result: CheckResult) -> None:
        self.result = result
        self.glyph.set_state(result.status.value)
        self.title_label.setText(result.title_for(i18n.language))
        self.summary_label.setText(result.summary_for(i18n.language))
        self.duration_label.setText(f"{result.duration_ms} ms" if result.duration_ms else "")
        self.details.setPlainText("\n".join(result.details) if result.details else "-")
        color = status_color(result.status.value)
        self.summary_label.setStyleSheet(f"color: {color};" if result.is_problem else "")

    def retranslate(self) -> None:
        self.set_result(self.result)

    def toggle_details(self) -> None:
        self.expanded = not self.expanded
        self.details.setVisible(self.expanded)
        self.details.setFixedHeight(118 if self.expanded else 0)
        self.expand_button.setText("⌃" if self.expanded else "⌄")
        self.toggled.emit(self.result.id)
        self.adjustSize()
