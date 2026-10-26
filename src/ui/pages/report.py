"""Экран отчёта: форматированный HTML, копирование, сохранение, «Поделиться»."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QTextBrowser, QVBoxLayout

from src.config.i18n import i18n
from src.core.history import History
from src.core.report_generator import ReportGenerator
from src.ui.pages.base_page import BasePage, make_card
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.sparkline import AvailabilityChart


class ReportPage(BasePage):
    """Готовый отчёт + кнопки экспорта."""

    message = pyqtSignal(str, str)

    def __init__(self, history: History, parent=None) -> None:
        super().__init__("report.title", "report.subtitle", parent)
        self.history = history
        self.generator: ReportGenerator | None = None

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_copy = AnimatedButton(variant="secondary", icon_name="copy")
        self.btn_save = AnimatedButton(variant="primary", icon_name="save")
        self.btn_share = AnimatedButton(variant="secondary", icon_name="share")
        self.btn_copy.clicked.connect(self.copy_report)
        self.btn_save.clicked.connect(self.save_report)
        self.btn_share.clicked.connect(self.share_report)
        buttons.addWidget(self.btn_copy)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_share)
        buttons.addStretch(1)
        from PyQt6.QtWidgets import QWidget  # noqa: PLC0415

        row = QWidget()
        row.setLayout(buttons)
        self.buttons_layout = buttons
        self.add_content(row)

        self.empty_label = QLabel()
        self.empty_label.setObjectName("muted")
        self.empty_label.setWordWrap(True)
        self.add_content(self.empty_label)

        self.view = QTextBrowser()
        self.view.setObjectName("reportView")
        self.view.setOpenExternalLinks(True)
        self.view.setMinimumHeight(360)
        self.view.setVisible(False)
        self.add_content(self.view, 1)

        chart_card = make_card()
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(14, 12, 14, 12)
        self.chart_title = QLabel()
        self.chart_title.setObjectName("cardTitle")
        self.chart = AvailabilityChart()
        chart_layout.addWidget(self.chart_title)
        chart_layout.addWidget(self.chart)
        self.add_content(chart_card)
        self.retranslate_ui()

    def set_report(self, generator: ReportGenerator) -> None:
        self.generator = generator
        self.view.setHtml(generator.to_html())
        self.view.setVisible(True)
        self.empty_label.setVisible(False)
        values = self.history.buckets(24, 24)
        availability = self.history.availability(24)
        self.chart.set_values(
            values,
            f"24h: {availability}%" if availability is not None else i18n.tr("dashboard.no_history"),
        )

    def copy_report(self) -> None:
        if not self.generator:
            self.message.emit(i18n.tr("report.empty"), "warn")
            return
        QApplication.clipboard().setText(self.generator.to_markdown())
        self.message.emit(i18n.tr("common.copied"), "ok")

    def save_report(self) -> None:
        if not self.generator:
            self.message.emit(i18n.tr("report.empty"), "warn")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("report.save_dialog"), "TwitchFix-report.md", i18n.tr("report.filters")
        )
        if path:
            self.generator.save(path)
            self.message.emit(f"{i18n.tr('common.saved')}: {path}", "ok")

    def share_report(self) -> None:
        if not self.generator:
            self.message.emit(i18n.tr("report.empty"), "warn")
            return
        QApplication.clipboard().setText(self.generator.share_text())
        self.message.emit(i18n.tr("report.share_done"), "ok")

    def set_narrow(self, narrow: bool) -> None:
        from PyQt6.QtWidgets import QBoxLayout  # noqa: PLC0415

        super().set_narrow(narrow)
        self.buttons_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        )
        self.view.setMinimumHeight(300 if narrow else 360)

    def retranslate_ui(self) -> None:
        super().retranslate_ui()
        self.btn_copy.setText(i18n.tr("common.copy"))
        self.btn_save.setText(i18n.tr("common.save"))
        self.btn_share.setText(i18n.tr("common.share"))
        self.empty_label.setText(i18n.tr("report.empty"))
        self.chart_title.setText(i18n.tr("dashboard.availability"))
        if self.generator:
            self.generator.language = i18n.language
            self.view.setHtml(self.generator.to_html())
