"""Кастомный title bar: градиентный логотип, drag окна, кнопки управления."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from src.config.constants import APP_NAME, APP_VERSION
from src.config.i18n import i18n
from src.ui.icons import app_logo_pixmap, icon
from src.ui.theme import palette


class GradientLabel(QWidget):
    """Текст с линейным градиентом (логотип TwitchFix)."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self._text = text
        font = QFont("Segoe UI", 11)
        font.setWeight(QFont.Weight.Bold)
        self.setFont(font)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_text(self, text: str) -> None:
        self._text = text
        self.updateGeometry()
        self.update()

    def sizeHint(self):  # type: ignore[override]
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self._text) + 4, 26)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        baseline = (self.height() + self.fontMetrics().height()) / 2 - self.fontMetrics().descent()
        path.addText(2, baseline, self.font(), self._text)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        from src.ui.theme import current_theme  # noqa: PLC0415

        if current_theme() == "light":
            gradient.setColorAt(0.0, QColor("#7f31ee"))
            gradient.setColorAt(0.5, QColor("#4b2180"))
            gradient.setColorAt(1.0, QColor("#9146ff"))
        else:
            gradient.setColorAt(0.0, QColor("#c9a7ff"))
            gradient.setColorAt(0.5, QColor("#ffffff"))
            gradient.setColorAt(1.0, QColor("#a970ff"))
        p.fillPath(path, QBrush(gradient))
        p.end()


class TitleBar(QFrame):
    """Верхняя панель frameless-окна."""

    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    compact_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(48)
        self._drag_position = None
        self._maximized = False

        self.logo = QLabel()
        self.logo.setFixedSize(30, 30)
        self.logo.setPixmap(app_logo_pixmap(30))
        self.logo.setStyleSheet("background: transparent;")

        self.title = GradientLabel(APP_NAME)
        self.subtitle = QLabel(i18n.tr("app.subtitle"))
        self.subtitle.setObjectName("titleSubLabel")
        self.version = QLabel(f"v{APP_VERSION}")
        self.version.setObjectName("muted")
        self.version.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.btn_minimize = self._make_button("minimize", i18n.tr("title.minimize"), self.minimize_clicked)
        self.btn_compact = self._make_button("compact", i18n.tr("title.compact"), self.compact_clicked, 30)
        self.btn_maximize = self._make_button("maximize", i18n.tr("title.maximize"), self.maximize_clicked)
        self.btn_close = self._make_button("close", i18n.tr("title.close"), self.close_clicked)
        self.btn_close.setObjectName("closeButton")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(10)
        layout.addWidget(self.logo)
        layout.addWidget(self.title)
        layout.addSpacing(8)
        layout.addWidget(self.subtitle, 1)
        layout.addWidget(self.version)
        layout.addSpacing(12)
        for button in (self.btn_minimize, self.btn_compact, self.btn_maximize, self.btn_close):
            layout.addWidget(button)

    def _make_button(
        self, icon_name: str, tooltip: str, signal: pyqtSignal, icon_size: int = 16
    ) -> QPushButton:
        button = QPushButton()
        button.setObjectName("windowButton")
        button.setFixedSize(34, 30)
        button.setIcon(icon(icon_name, palette().text, icon_size))
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(signal)
        return button

    def set_maximized(self, maximized: bool) -> None:
        self._maximized = maximized
        name = "restore" if maximized else "maximize"
        self.btn_maximize.setIcon(icon(name, palette().text, 16))
        self.btn_maximize.setToolTip(i18n.tr("title.restore" if maximized else "title.maximize"))

    def refresh_icons(self) -> None:
        color = palette().text
        for button, name in (
            (self.btn_minimize, "minimize"),
            (self.btn_compact, "compact"),
            (self.btn_maximize, "restore" if self._maximized else "maximize"),
            (self.btn_close, "close"),
        ):
            button.setIcon(icon(name, color, 16))
        self.logo.setPixmap(app_logo_pixmap(30))

    def set_compact(self, compact: bool) -> None:
        """В узком окне скрываем подзаголовок, версию и второстепенные кнопки."""
        self.subtitle.setVisible(not compact)
        self.version.setVisible(not compact)
        self.btn_maximize.setVisible(not compact)
        self.btn_compact.setVisible(not compact)
        self.title.setVisible(True)

    def retranslate_ui(self) -> None:
        self.subtitle.setText(i18n.tr("app.subtitle"))
        self.btn_minimize.setToolTip(i18n.tr("title.minimize"))
        self.btn_compact.setToolTip(i18n.tr("title.compact"))
        self.btn_close.setToolTip(i18n.tr("title.close"))
        self.set_maximized(self._maximized)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            handle = window.windowHandle() if window else None
            if handle is not None and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
                return
            self._drag_position = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        # Ручной fallback для платформ без startSystemMove.
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_position
            self.window().move(self.window().pos() + delta)
            self._drag_position = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_clicked.emit()
        super().mouseDoubleClickEvent(event)
