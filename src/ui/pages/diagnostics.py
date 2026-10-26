"""Экран диагностики: прогресс, появляющиеся карточки проверок, терминальный лог."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config.i18n import i18n
from src.core.diagnostics import check_by_id
from src.core.diagnostics.base_check import CheckResult, Status
from src.ui.pages.base_page import make_card
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.check_item import CheckItem
from src.ui.widgets.progress_bar import GradientProgressBar
from src.ui.widgets.terminal_log import TerminalLog


class DiagnosticsPage(QWidget):
    """Страница выполнения 13 проверок."""

    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    open_report = pyqtSignal()
    message = pyqtSignal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self.items: dict[str, CheckItem] = {}
        self.results: list[CheckResult] = []
        self._running = False

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(14)
        self.root_layout = root
        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("pageSubtitle")
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)

        # Лог создаём заранее: кнопки подключаются к нему ниже.
        self.log = TerminalLog()
        self.log.setFixedHeight(140)

        # Карточка прогресса.
        progress_card = make_card()
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(16, 14, 16, 14)
        progress_layout.setSpacing(10)
        self.progress_label = QLabel()
        self.progress_label.setObjectName("sectionTitle")
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("muted")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        top_row = QHBoxLayout()
        top_row.addWidget(self.progress_label, 1)
        top_row.addWidget(self.percent_label)
        progress_layout.addLayout(top_row)
        self.progress = GradientProgressBar()
        progress_layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_start = AnimatedButton(variant="primary", icon_name="play")
        self.btn_stop = AnimatedButton(variant="secondary", icon_name="stop")
        self.btn_clear = AnimatedButton(variant="ghost", icon_name="trash")
        self.btn_report = AnimatedButton(variant="ghost", icon_name="report")
        self.btn_start.clicked.connect(self.start_requested)
        self.btn_stop.clicked.connect(self.stop_requested)
        self.btn_clear.clicked.connect(self.log.clear_log)
        self.btn_report.clicked.connect(self.open_report)
        self.btn_stop.setEnabled(False)
        buttons.addWidget(self.btn_start)
        buttons.addWidget(self.btn_stop)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_clear)
        buttons.addWidget(self.btn_report)
        progress_layout.addLayout(buttons)
        self.buttons_layout = buttons
        root.addWidget(progress_card)

        # Список проверок (прокрутка) + лог.
        self.checks_scroll = QScrollArea()
        self.checks_scroll.setObjectName("pageScrollArea")
        self.checks_scroll.setWidgetResizable(True)
        self.checks_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.checks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.checks_container = QWidget()
        self.checks_layout = QVBoxLayout(self.checks_container)
        self.checks_layout.setContentsMargins(2, 2, 8, 8)
        self.checks_layout.setSpacing(10)
        self.checks_layout.addStretch(1)
        self.checks_scroll.setWidget(self.checks_container)
        self.checks_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.checks_scroll, 3)

        terminal_frame = make_card("terminalFrame")
        terminal_layout = QVBoxLayout(terminal_frame)
        terminal_layout.setContentsMargins(10, 10, 10, 10)
        terminal_layout.setSpacing(6)
        self.log_title = QLabel()
        self.log_title.setObjectName("sectionTitle")
        terminal_layout.addWidget(self.log_title)
        terminal_layout.addWidget(self.log)
        root.addWidget(terminal_frame, 1)

        self.retranslate_ui()
        self.log.append_line(i18n.tr("diagnostics.empty"), "debug")

    # ------------------------------------------------------------ движок
    def on_started(self, pending: list[CheckResult]) -> None:
        self._running = True
        self.results = []
        self.items.clear()
        while self.checks_layout.count() > 1:
            item = self.checks_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.progress.setValue(0, animate=False)
        self.percent_label.setText("0%")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log.clear_log()
        self.log.append_line(f"TwitchFix: {len(pending)} checks queued", "info")
        _ = pending  # карточки создаются по сигналу check_started

    def on_check_started(self, check_id: str) -> None:
        cls = check_by_id(check_id)
        placeholder = CheckResult(
            id=check_id,
            title=cls.title_ru if cls else check_id,
            title_en=cls.title_en if cls else check_id,
            status=Status.RUNNING,
            summary=i18n.tr("common.running"),
            summary_en="Running…",
        )
        item = CheckItem(placeholder)
        self.items[check_id] = item
        self.checks_layout.insertWidget(self.checks_layout.count() - 1, item)
        self.log.append_line(f"→ {placeholder.title_for(i18n.language)}", "debug")

    def on_check_finished(self, result: CheckResult) -> None:
        self.results.append(result)
        item = self.items.get(result.id)
        if item is None:
            self.on_check_started(result.id)
            item = self.items.get(result.id)
        if item is not None:
            item.set_result(result)
        level = {"ok": "ok", "warning": "warn", "error": "err"}.get(result.status.value, "info")
        self.log.append_line(f"{result.title_for(i18n.language)}: {result.summary_for(i18n.language)}", level)

    def on_progress(self, done: int, total: int, label: str) -> None:
        percent = int(done / max(1, total) * 100)
        self.progress.setValue(percent)
        self.percent_label.setText(f"{percent}%")
        self.progress_label.setText(f"{i18n.tr('diagnostics.progress')}: {done}/{total} — {label}")

    def on_finished(self, results: list[CheckResult]) -> None:
        self._running = False
        self.results = results
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setValue(100)
        duration = sum(item.duration_ms for item in results) / 1000
        self.log.append_line(i18n.tr("diagnostics.completed", len(results), f"{duration:.1f}s"), "ok")
        self.message.emit(i18n.tr("diagnostics.completed", len(results), f"{duration:.1f}s"), "ok")

    def append_log(self, level: str, message: str) -> None:
        if level != "info" or "started" in message or "finished" in message:
            self.log.append_line(message, level)

    def expand_check(self, check_id: str) -> None:
        item = self.items.get(check_id)
        if item and not item.expanded:
            item.toggle_details()

    def set_narrow(self, narrow: bool) -> None:
        from PyQt6.QtWidgets import QBoxLayout  # noqa: PLC0415

        margin = 14 if narrow else 26
        self.root_layout.setContentsMargins(margin, 18 if narrow else 22, margin, 18 if narrow else 22)
        self.buttons_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        )
        self.log.setFixedHeight(110 if narrow else 140)

    # --------------------------------------------------------- локализация
    def retranslate_ui(self) -> None:
        self.title_label.setText(i18n.tr("diagnostics.title"))
        self.subtitle_label.setText(i18n.tr("diagnostics.subtitle"))
        self.progress_label.setText(f"{i18n.tr('diagnostics.progress')}: 0/13")
        self.log_title.setText(i18n.tr("diagnostics.log"))
        self.btn_start.setText(i18n.tr("diagnostics.start"))
        self.btn_stop.setText(i18n.tr("diagnostics.stop"))
        self.btn_clear.setText(i18n.tr("diagnostics.clear_log"))
        self.btn_report.setText(i18n.tr("nav.report"))
        for item in self.items.values():
            item.retranslate()
