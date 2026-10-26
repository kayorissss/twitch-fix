"""Всплывающие уведомления внутри окна (fade + slide, авто-скрытие)."""
from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QTimer,
)
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from src.ui.icons import icon_pixmap
from src.ui.theme import palette, status_color

LEVEL_TO_STATUS = {"info": "info", "ok": "ok", "success": "ok", "warn": "warning", "err": "error"}


class Toast(QFrame):
    """Одно уведомление."""

    def __init__(self, parent: QWidget, message: str, level: str = "info") -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("card", "true")
        self.setFixedHeight(46)
        self.setMinimumWidth(260)
        color = status_color(LEVEL_TO_STATUS.get(level, "info"))
        self.setStyleSheet(
            f"QFrame#toast {{ background: {palette().surface}; border: 1px solid {color}; "
            "border-radius: 10px; }"
        )
        icon_label = QLabel()
        icon_label.setPixmap(
            icon_pixmap("info" if level == "info" else ("check" if level in ("ok", "success") else "warning"), color, 18)
        )
        text = QLabel(message)
        text.setWordWrap(True)
        text.setStyleSheet("color: " + palette().text + ";")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        layout.addWidget(icon_label)
        layout.addWidget(text, 1)
        self.adjustSize()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.hide()
        super().mousePressEvent(event)


class ToastManager(QObject):
    """Создаёт и позиционирует тосты в правом верхнем углу окна."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.parent_widget = parent
        self.toasts: list[Toast] = []
        parent.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self.parent_widget and event.type() == QEvent.Type.Resize:
            self._reposition()
        return super().eventFilter(watched, event)

    def show(self, message: str, level: str = "info", duration: int = 3800) -> None:
        toast = Toast(self.parent_widget, message, level)
        toast.show()
        self.toasts.append(toast)
        y = 68 + sum(item.height() + 8 for item in self.toasts[:-1])
        final_pos = QPoint(
            max(12, self.parent_widget.width() - toast.width() - 22), y
        )
        toast.move(final_pos.x() + 40, final_pos.y())
        self._animate(toast, final_pos, entering=True)

        timer = QTimer(toast)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._dismiss(toast))
        timer.start(duration)
        while len(self.toasts) > 4:
            old = self.toasts.pop(0)
            old.deleteLater()
        self._reposition()

    def _animate(self, toast: Toast, target: QPoint, entering: bool) -> None:
        effect = QGraphicsOpacityEffect(toast)
        effect.setOpacity(0.0 if entering else 1.0)
        toast.setGraphicsEffect(effect)
        group = QParallelAnimationGroup(toast)
        opacity = QPropertyAnimation(effect, b"opacity", group)
        opacity.setDuration(260)
        opacity.setStartValue(0.0 if entering else 1.0)
        opacity.setEndValue(1.0 if entering else 0.0)
        slide = QPropertyAnimation(toast, b"pos", group)
        slide.setDuration(300)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide.setStartValue(toast.pos())
        slide.setEndValue(target)
        group.addAnimation(opacity)
        group.addAnimation(slide)
        if not entering:
            group.finished.connect(toast.deleteLater)
        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _dismiss(self, toast: Toast) -> None:
        if toast in self.toasts:
            self.toasts.remove(toast)
        self._animate(toast, QPoint(toast.x() + 40, toast.y()), entering=False)
        self._reposition()

    def _reposition(self) -> None:
        y = 68
        for toast in self.toasts:
            toast.move(max(12, self.parent_widget.width() - toast.width() - 22), y)
            y += toast.height() + 8
