"""Общий каркас страницы: заголовок + прокручиваемое содержимое."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from src.config.i18n import i18n


def make_card(object_name: str = "") -> QFrame:
    """Создать карточку со стилем QSS [card="true"]."""
    card = QFrame()
    card.setProperty("card", "true")
    if object_name:
        card.setObjectName(object_name)
    return card


class BasePage(QWidget):
    """Базовая страница: заголовок, подзаголовок, QScrollArea, контент."""

    def __init__(self, title_key: str, subtitle_key: str, parent=None) -> None:
        super().__init__(parent)
        self.title_key = title_key
        self.subtitle_key = subtitle_key
        self.setObjectName("page")

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(26, 22, 26, 22)
        self.root.setSpacing(16)

        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.root.addWidget(self.title_label)
        self.root.addWidget(self.subtitle_label)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("pageScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content = QVBoxLayout(self.container)
        self.content.setContentsMargins(2, 4, 8, 12)
        self.content.setSpacing(14)
        self.scroll.setWidget(self.container)
        self.root.addWidget(self.scroll, 1)
        self.content.addStretch(1)
        # Не вызываем retranslate_ui() здесь: переопределённый метод страницы
        # может обращаться к виджетам, которые ещё не созданы.
        self.title_label.setText(i18n.tr(title_key))
        self.subtitle_label.setText(i18n.tr(subtitle_key))

    def insert_content(self, index: int, widget: QWidget, stretch: int = 0) -> None:
        """Добавить виджет перед финальным stretch."""
        self.content.insertWidget(min(index, self.content.count() - 1), widget, stretch)

    def add_content(self, widget: QWidget, stretch: int = 0) -> None:
        self.insert_content(self.content.count() - 1, widget, stretch)

    def set_narrow(self, narrow: bool) -> None:
        """Адаптировать отступы под компактное окно 400x600."""
        margin = 14 if narrow else 26
        self.root.setContentsMargins(margin, 18 if narrow else 22, margin, 18 if narrow else 22)
        self.content.setContentsMargins(2, 4, 4 if narrow else 8, 12)

    def retranslate_ui(self) -> None:
        self.title_label.setText(i18n.tr(self.title_key))
        self.subtitle_label.setText(i18n.tr(self.subtitle_key))
