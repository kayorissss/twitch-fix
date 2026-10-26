"""Главный экран: hero-статус, кнопки запуска, 6 мини-карточек, график 24ч."""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QBoxLayout, QComboBox, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.config.i18n import i18n
from src.core.diagnostics.base_check import CheckResult, Status, overall_status
from src.core.history import History
from src.ui.pages.base_page import BasePage, make_card
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.sparkline import AvailabilityChart
from src.ui.widgets.status_card import StatusCard

MINI_CARDS: list[tuple[str, str, str]] = [
    ("dns", "card.dns", "globe"),
    ("hosts", "card.hosts", "file"),
    ("ssl", "card.ssl", "lock"),
    ("proxy", "card.proxy", "route"),
    ("firewall", "card.firewall", "shield"),
    ("process", "card.process", "apps"),
]


class DashboardPage(BasePage):
    """Обзор подключения к Twitch."""

    run_diagnostics = pyqtSignal()
    quick_fix = pyqtSignal()
    open_report = pyqtSignal()
    card_clicked = pyqtSignal(str)
    message = pyqtSignal(str, str)

    def __init__(self, history: History, parent=None) -> None:
        super().__init__("dashboard.title", "dashboard.subtitle", parent)
        self.history = history

        # Hero-карточка статуса.
        self.hero = StatusCard("overall", "", "rocket", kind="hero")
        self.hero.setMinimumHeight(150)
        self.hero.clicked.connect(lambda _id: self.open_report.emit())
        self.add_content(self.hero)

        # Кнопки действий.
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.btn_run = AnimatedButton(variant="primary", icon_name="rocket")
        self.btn_quick = AnimatedButton(variant="secondary", icon_name="wrench")
        self.btn_report = AnimatedButton(variant="ghost", icon_name="report")
        self.btn_run.setMinimumWidth(230)
        self.btn_quick.setMinimumWidth(180)
        self.btn_report.setMinimumWidth(110)
        self.btn_run.clicked.connect(self.run_diagnostics)
        self.btn_quick.clicked.connect(self.quick_fix)
        self.btn_report.clicked.connect(self.open_report)
        actions.addWidget(self.btn_run, 3)
        actions.addWidget(self.btn_quick, 2)
        actions.addWidget(self.btn_report, 1)
        actions_widget = QWidget()
        actions_widget.setLayout(actions)
        self.actions_layout = actions
        self.add_content(actions_widget)

        self.last_check_label = QLabel()
        self.last_check_label.setObjectName("muted")
        self.add_content(self.last_check_label)

        # Быстрый статус (2x3) + график доступности.
        self.cards_title = QLabel()
        self.cards_title.setObjectName("sectionTitle")
        self.add_content(self.cards_title)
        overview = QHBoxLayout()
        overview.setSpacing(14)
        grid_widget = QWidget()
        grid_widget.setMinimumWidth(0)
        grid = QGridLayout(grid_widget)
        self.grid = grid
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self.cards: dict[str, StatusCard] = {}
        for index, (check_id, key, icon_name) in enumerate(MINI_CARDS):
            card = StatusCard(check_id, i18n.tr(key), icon_name)
            card.setMinimumWidth(0)
            card.clicked.connect(self.card_clicked)
            grid.addWidget(card, index // 2, index % 2)
            self.cards[check_id] = card
        overview.addWidget(grid_widget, 3)

        chart_card = make_card()
        chart_card.setMinimumWidth(230)
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(14, 14, 14, 10)
        chart_layout.setSpacing(8)
        chart_header = QHBoxLayout()
        self.chart_title = QLabel()
        self.chart_title.setObjectName("cardTitle")
        self.period_combo = QComboBox()
        self.period_combo.setFixedWidth(108)
        self.period_combo.addItem(i18n.tr("dashboard.period_24h"), 24)
        self.period_combo.addItem(i18n.tr("dashboard.period_7d"), 168)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        chart_header.addWidget(self.chart_title, 1)
        chart_header.addWidget(self.period_combo)
        self.chart = AvailabilityChart()
        chart_layout.addLayout(chart_header)
        chart_layout.addWidget(self.chart)
        chart_layout.addStretch(1)
        overview.addWidget(chart_card, 2)
        overview_widget = QWidget()
        overview_widget.setMinimumWidth(0)
        overview_widget.setLayout(overview)
        overview_widget.setMinimumHeight(300)
        self.overview_layout = overview
        self.chart_card = chart_card
        self.overview_widget = overview_widget
        self.add_content(overview_widget)

        self.set_results([])
        self.retranslate_ui()

    # -------------------------------------------------------------- данные
    def set_results(self, results: list[CheckResult]) -> None:
        """Обновить hero и мини-карточки по результатам диагностики."""
        self.last_results = results
        if not results:
            self.hero.set_status(
                "info",
                i18n.tr("dashboard.status_unknown"),
                i18n.tr("dashboard.status_unknown_hint"),
            )
            self.hero.set_title("TwitchFix")
            for card in self.cards.values():
                card.set_status("info", i18n.tr("common.not_checked"))
            self.last_check_label.setText(i18n.tr("dashboard.last_check", i18n.tr("dashboard.never")))
        else:
            status = overall_status(results)
            problems = [item for item in results if item.is_problem]
            if status in (Status.ERROR, Status.WARNING):
                self.hero.set_status(
                    "error" if status == Status.ERROR else "warning",
                    i18n.tr("dashboard.status_problem"),
                    i18n.tr("dashboard.status_problem_hint")
                    + (f" ({len(problems)})" if problems else ""),
                )
            else:
                self.hero.set_status("ok", i18n.tr("dashboard.status_ok"), i18n.tr("dashboard.status_ok_hint"))
            self.hero.set_title("TwitchFix")
            for check_id, card in self.cards.items():
                result = next((item for item in results if item.id == check_id), None)
                if result is None:
                    card.set_status("info", i18n.tr("common.not_checked"))
                else:
                    card.set_status(result.status.value, result.summary_for(i18n.language))
            stamp = datetime.fromtimestamp(max(item.timestamp for item in results)).strftime("%d.%m.%Y %H:%M")
            self.last_check_label.setText(i18n.tr("dashboard.last_check", stamp))
        self.update_chart()

    def set_checking(self, checking: bool) -> None:
        self.btn_run.setEnabled(not checking)
        self.btn_quick.setEnabled(not checking)
        if checking:
            self.hero.set_status("running", i18n.tr("dashboard.status_checking"), "")

    def _on_period_changed(self, _index: int) -> None:
        self.update_chart()

    def update_chart(self) -> None:
        hours = int(self.period_combo.currentData() or 24)
        values = self.history.buckets(hours, 24 if hours <= 24 else 28)
        availability = self.history.availability(hours)
        period = i18n.tr("dashboard.period_24h" if hours <= 24 else "dashboard.period_7d")
        label = (
            f"{period}: {availability}%"
            if availability is not None
            else i18n.tr("dashboard.no_history")
        )
        self.chart.set_values(values, label)
        self.chart_title.setText(i18n.tr("dashboard.availability"))

    def set_narrow(self, narrow: bool) -> None:
        """В узком окне кнопки и карточки выстраиваются в одну колонку."""
        super().set_narrow(narrow)
        direction = QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        self.actions_layout.setDirection(direction)
        self.overview_layout.setDirection(direction)
        for index, (check_id, _, _) in enumerate(MINI_CARDS):
            card = self.cards.get(check_id)
            if card:
                self.grid.addWidget(card, index if narrow else index // 2, 0 if narrow else index % 2)
        self.overview_widget.setMinimumHeight(560 if narrow else 300)

    # ------------------------------------------------------------- локализация
    def retranslate_ui(self) -> None:
        super().retranslate_ui()
        self.btn_run.setText(i18n.tr("common.run_diagnostics"))
        self.btn_quick.setText(i18n.tr("common.quick_fix"))
        self.btn_report.setText(i18n.tr("nav.report"))
        self.cards_title.setText(i18n.tr("dashboard.cards"))
        self.chart_title.setText(i18n.tr("dashboard.availability"))
        current = self.period_combo.currentData()
        self.period_combo.blockSignals(True)
        self.period_combo.setItemText(0, i18n.tr("dashboard.period_24h"))
        self.period_combo.setItemText(1, i18n.tr("dashboard.period_7d"))
        self.period_combo.setCurrentIndex(max(0, self.period_combo.findData(current)))
        self.period_combo.blockSignals(False)
        for check_id, card in self.cards.items():
            key = next(item[1] for item in MINI_CARDS if item[0] == check_id)
            card.set_title(i18n.tr(key))
            card.refresh_icon()
        self.hero.refresh_icon()
        self.set_results(getattr(self, "last_results", []))
