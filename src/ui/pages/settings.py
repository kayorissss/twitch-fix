"""Экран настроек: автозапуск, язык, тема, уведомления, мониторинг, о программе."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from src.config.constants import APP_NAME, APP_VERSION, GITHUB_URL
from src.config.i18n import i18n
from src.ui.pages.base_page import BasePage, make_card
from src.ui.widgets.animated_button import AnimatedButton


class SettingsPage(BasePage):
    """Управление пользовательскими настройками (QSettings)."""

    theme_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    settings_changed = pyqtSignal(str, object)
    open_logs = pyqtSignal()
    reset_settings = pyqtSignal()

    def __init__(self, settings: Any, parent=None) -> None:
        super().__init__("settings.title", "settings.subtitle", parent)
        self.settings = settings

        general = make_card()
        general_layout = QVBoxLayout(general)
        general_layout.setContentsMargins(18, 16, 18, 16)
        general_layout.setSpacing(12)
        self.general_title = QLabel()
        self.general_title.setObjectName("sectionTitle")

        self.autostart = QCheckBox()
        self.notifications = QCheckBox()
        self.monitoring = QCheckBox()
        self.autostart.toggled.connect(lambda value: self._changed("autostart", bool(value)))
        self.notifications.toggled.connect(lambda value: self._changed("notifications", bool(value)))
        self.monitoring.toggled.connect(lambda value: self._changed("monitoring", bool(value)))
        general_layout.addWidget(self.general_title)
        general_layout.addWidget(self.autostart)
        general_layout.addWidget(self.notifications)
        general_layout.addWidget(self.monitoring)

        form = QGridLayout()
        form.setSpacing(10)
        form.setColumnStretch(1, 1)
        self.language_label = QLabel()
        self.theme_label = QLabel()
        self.interval_label = QLabel()
        self.history_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItem("Русский", "ru")
        self.language_combo.addItem("English", "en")
        self.theme_combo = QComboBox()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.history_spin = QSpinBox()
        self.history_spin.setRange(1, 90)
        self.language_combo.currentIndexChanged.connect(
            lambda _: self._changed("language", self.language_combo.currentData())
        )
        self.theme_combo.currentIndexChanged.connect(
            lambda _: self._changed("theme", self.theme_combo.currentData())
        )
        self.interval_spin.valueChanged.connect(lambda value: self._changed("monitor_interval", value))
        self.history_spin.valueChanged.connect(lambda value: self._changed("history_days", value))
        form.addWidget(self.language_label, 0, 0)
        form.addWidget(self.language_combo, 0, 1)
        form.addWidget(self.theme_label, 1, 0)
        form.addWidget(self.theme_combo, 1, 1)
        form.addWidget(self.interval_label, 2, 0)
        form.addWidget(self.interval_spin, 2, 1)
        form.addWidget(self.history_label, 3, 0)
        form.addWidget(self.history_spin, 3, 1)
        general_layout.addLayout(form)
        self.restart_hint = QLabel()
        self.restart_hint.setObjectName("muted")
        general_layout.addWidget(self.restart_hint)
        self.add_content(general)

        about = make_card()
        about_layout = QVBoxLayout(about)
        about_layout.setContentsMargins(18, 16, 18, 16)
        about_layout.setSpacing(10)
        self.about_title = QLabel()
        self.about_title.setObjectName("sectionTitle")
        self.version_label = QLabel(f"{APP_NAME} v{APP_VERSION}")
        self.github_label = QLabel(f'<a href="{GITHUB_URL}" style="color:#a970ff">{GITHUB_URL}</a>')
        self.github_label.setOpenExternalLinks(True)
        self.github_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.btn_logs = AnimatedButton(variant="secondary", icon_name="folder")
        self.btn_reset = AnimatedButton(variant="ghost", icon_name="refresh")
        self.btn_logs.clicked.connect(self.open_logs)
        self.btn_reset.clicked.connect(self.reset_settings)
        row = QHBoxLayout()
        row.addWidget(self.btn_logs)
        row.addWidget(self.btn_reset)
        row.addStretch(1)
        self.about_row = row
        about_layout.addWidget(self.about_title)
        about_layout.addWidget(self.version_label)
        about_layout.addWidget(self.github_label)
        about_layout.addLayout(row)
        self.add_content(about)

        self.sync_from_settings()
        self.retranslate_ui()

    # ------------------------------------------------------------ настройки
    def _changed(self, key: str, value: object) -> None:
        self.settings.set(key, value)
        self.settings_changed.emit(key, value)
        if key == "theme":
            self.theme_changed.emit(str(value))
        elif key == "language":
            self.language_changed.emit(str(value))

    def sync_from_settings(self) -> None:
        """Прочитать значения из QSettings без генерации сигналов."""
        blockers = [
            QSignalBlocker(widget)
            for widget in (
                self.autostart, self.notifications, self.monitoring,
                self.language_combo, self.theme_combo, self.interval_spin, self.history_spin,
            )
        ]
        self.autostart.setChecked(bool(self.settings.get("autostart")))
        self.notifications.setChecked(bool(self.settings.get("notifications")))
        self.monitoring.setChecked(bool(self.settings.get("monitoring")))
        language = str(self.settings.get("language"))
        self.language_combo.setCurrentIndex(0 if self.language_combo.findData(language) < 0 else self.language_combo.findData(language))
        theme = str(self.settings.get("theme"))
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(theme)))
        self.interval_spin.setValue(int(self.settings.get("monitor_interval")))
        self.history_spin.setValue(int(self.settings.get("history_days")))
        del blockers

    def set_narrow(self, narrow: bool) -> None:
        from PyQt6.QtWidgets import QBoxLayout  # noqa: PLC0415

        super().set_narrow(narrow)
        self.about_row.setDirection(
            QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        )

    # --------------------------------------------------------- локализация
    def retranslate_ui(self) -> None:
        super().retranslate_ui()
        self.general_title.setText(i18n.tr("settings.general"))
        self.autostart.setText(i18n.tr("settings.autostart"))
        self.notifications.setText(i18n.tr("settings.notifications"))
        self.monitoring.setText(i18n.tr("settings.monitoring"))
        self.language_label.setText(i18n.tr("settings.language"))
        self.theme_label.setText(i18n.tr("settings.theme"))
        self.interval_label.setText(i18n.tr("settings.monitor_interval"))
        self.history_label.setText(i18n.tr("settings.history_days"))
        self.restart_hint.setText(i18n.tr("settings.restart_hint"))
        self.about_title.setText(i18n.tr("settings.about"))
        self.btn_logs.setText(i18n.tr("settings.logs"))
        self.btn_reset.setText(i18n.tr("settings.reset"))
        blocker = QSignalBlocker(self.theme_combo)
        current = self.theme_combo.currentData()
        self.theme_combo.clear()
        self.theme_combo.addItem(i18n.tr("settings.dark"), "dark")
        self.theme_combo.addItem(i18n.tr("settings.light"), "light")
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(current)))
        del blocker
