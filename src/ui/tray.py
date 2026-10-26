"""Системный трей: иконка, контекстное меню, уведомления мониторинга."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from src.config.i18n import i18n
from src.ui.icons import app_icon


class TrayManager(QObject):
    """Оборачивает QSystemTrayIcon и отправляет сигналы в главное окно."""

    show_window = pyqtSignal()
    check_now = pyqtSignal()
    quit_app = pyqtSignal()

    def __init__(self, parent: QObject | None = None, notifications: bool = True) -> None:
        super().__init__(parent)
        self.notifications_enabled = notifications
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("TwitchFix")
        self.tray.activated.connect(self._on_activated)
        self.menu = QMenu()
        self.action_show = self.menu.addAction(i18n.tr("common.show"))
        self.action_check = self.menu.addAction(i18n.tr("common.check_now"))
        self.menu.addSeparator()
        self.action_quit = self.menu.addAction(i18n.tr("common.close_app"))
        self.action_show.triggered.connect(self.show_window)
        self.action_check.triggered.connect(self.check_now)
        self.action_quit.triggered.connect(self.quit_app)
        self.tray.setContextMenu(self.menu)
        self.tray.show()

    @staticmethod
    def is_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def set_status(self, ok: bool, message: str = "") -> None:
        status = "● OK" if ok else "● OFFLINE"
        self.tray.setToolTip(f"TwitchFix — {status}\n{message}".strip())

    def notify(self, title: str, message: str, level: str = "info") -> None:
        if not self.notifications_enabled:
            return
        icon_type = {
            "ok": QSystemTrayIcon.MessageIcon.Information,
            "info": QSystemTrayIcon.MessageIcon.Information,
            "warn": QSystemTrayIcon.MessageIcon.Warning,
            "err": QSystemTrayIcon.MessageIcon.Critical,
        }.get(level, QSystemTrayIcon.MessageIcon.Information)
        self.tray.showMessage(title, message, icon_type, 6000)

    def set_notifications(self, enabled: bool) -> None:
        self.notifications_enabled = enabled

    def retranslate_ui(self) -> None:
        self.action_show.setText(i18n.tr("common.show"))
        self.action_check.setText(i18n.tr("common.check_now"))
        self.action_quit.setText(i18n.tr("common.close_app"))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window.emit()
