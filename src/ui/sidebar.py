"""Сайдбар: 60px свёрнутый / 200px развёрнутый, иконки, тултипы, hover."""
from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from src.config.constants import APP_VERSION, SIDEBAR_COLLAPSED, SIDEBAR_EXPANDED
from src.config.i18n import i18n
from src.ui.icons import icon
from src.ui.theme import palette

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("home", "nav.dashboard", "Главная"),
    ("search", "nav.diagnostics", "Диагностика"),
    ("wrench", "nav.autofix", "Авто-исправление"),
    ("report", "nav.report", "Отчёт"),
    ("settings", "nav.settings", "Настройки"),
]


class Sidebar(QFrame):
    """Левая навигационная панель с анимацией ширины."""

    page_changed = pyqtSignal(int)

    def __init__(self, parent=None, expanded: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._expanded = expanded
        self._active = 0
        self.setFixedWidth(SIDEBAR_EXPANDED if expanded else SIDEBAR_COLLAPSED)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 14, 8, 12)
        layout.setSpacing(6)

        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("ghostButton")
        self.toggle_button.setFixedHeight(34)
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_button)
        layout.addSpacing(8)

        self.buttons: list[QPushButton] = []
        for index, (icon_name, key, _) in enumerate(NAV_ITEMS):
            button = QPushButton()
            button.setObjectName("navButton")
            button.setIcon(icon(icon_name, palette().text, 20))
            button.setIconSize(QSize(20, 20))
            button.setFixedHeight(42)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("active", "true" if index == 0 else "false")
            button.clicked.connect(lambda checked=False, i=index: self.set_active(i, emit=True))
            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch(1)
        self.version_label = QLabel(f"TwitchFix v{APP_VERSION}")
        self.version_label.setObjectName("sideVersion")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.version_label)
        self.retranslate_ui()

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        """Свернуть/развернуть панель (без анимации — для компактного режима)."""
        self._expanded = expanded
        target = SIDEBAR_EXPANDED if expanded else SIDEBAR_COLLAPSED
        if not animate:
            self.setMinimumWidth(target)
            self.setMaximumWidth(target)
            self.setFixedWidth(target)
            self.retranslate_ui()
            return
        start = self.width()
        self.setMinimumWidth(min(start, target))
        self.setMaximumWidth(max(start, target))
        group = QParallelAnimationGroup(self)
        for prop in (b"minimumWidth", b"maximumWidth"):
            animation = QPropertyAnimation(self, prop, group)
            animation.setDuration(230)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.setStartValue(start)
            animation.setEndValue(target)
            group.addAnimation(animation)
        group.finished.connect(lambda: (self.setMinimumWidth(target), self.setMaximumWidth(target)))
        setattr(self, "_width_animation", group)
        group.start()
        self.retranslate_ui()

    def set_active(self, index: int, emit: bool = False) -> None:
        self._active = index
        for i, button in enumerate(self.buttons):
            button.setProperty("active", "true" if i == index else "false")
            button.style().polish(button)
        if emit:
            self.page_changed.emit(index)

    def refresh_icons(self) -> None:
        color = palette().text
        for button, (icon_name, _, _) in zip(self.buttons, NAV_ITEMS):
            button.setIcon(icon(icon_name, color, 20))
        self.toggle_button.setIcon(icon("chevron", color, 18))

    def retranslate_ui(self) -> None:
        for button, (_, key, fallback) in zip(self.buttons, NAV_ITEMS):
            label = i18n.tr(key)
            if self._expanded:
                button.setText("   " + label)
                button.setToolTip(label)
            else:
                button.setText("")
                button.setToolTip(label)
            button.setIconSize(QSize(20, 20))
        self.toggle_button.setText(
            ("   " + i18n.tr("nav.collapse")) if self._expanded else ""
        )
        self.toggle_button.setToolTip(i18n.tr("nav.collapse" if self._expanded else "nav.expand"))
        self.toggle_button.setIcon(icon("chevron", palette().text_muted, 18))
        self.version_label.setText(f"v{APP_VERSION}" if not self._expanded else f"TwitchFix v{APP_VERSION}")
