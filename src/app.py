"""QApplication и точка входа в GUI.

Создаёт настройки, применяет тему/язык, строит главное окно и (при наличии)
системный трей. ``setQuitOnLastWindowClosed(False)`` позволяет работать в трее
после сворачивания окна.
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.config.constants import APP_NAME, APP_ORG, APP_VERSION
from src.config.i18n import i18n
from src.config.settings import AppSettings
from src.ui import theme as theme_module
from src.ui.icons import app_icon
from src.ui.main_window import MainWindow
from src.utils.logger import get_logger, install_excepthook

log = get_logger(__name__)


class TwitchFixApplication(QApplication):
    """Глобальное состояние GUI-приложения."""

    def __init__(self, argv: list[str] | None = None) -> None:
        # Политику HiDPI нужно задать ДО создания экземпляра QApplication.
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except AttributeError:
            pass
        super().__init__(argv or sys.argv)
        self.setApplicationName(APP_NAME)
        self.setApplicationDisplayName(APP_NAME)
        self.setOrganizationName(APP_ORG)
        self.setApplicationVersion(APP_VERSION)
        self.setWindowIcon(app_icon())
        self.setQuitOnLastWindowClosed(False)
        font = QFont("Segoe UI")
        font.setPointSize(10)
        self.setFont(font)

        self.settings = AppSettings()
        i18n.set_language(str(self.settings.get("language")))
        theme_module.load_theme(str(self.settings.get("theme")))
        self.window = MainWindow(self.settings)
        install_excepthook()
        log.info("%s v%s started (Python %s, %s)", APP_NAME, APP_VERSION, sys.version.split()[0], sys.platform)
