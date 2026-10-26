"""Экран авто-исправления: карточки проблем, подтверждения, «Исправить всё»."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.config.i18n import i18n
from src.core.diagnostics.base_check import CheckResult
from src.core.fixes import fixes_for_results
from src.core.fixes.base_fix import BaseFix, FixResult
from src.ui.pages.base_page import BasePage, make_card
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.progress_bar import GradientProgressBar


class ProblemCard(QWidget):
    """Одна проблема + описание исправления + кнопки."""

    def __init__(self, fix: BaseFix, result: CheckResult, parent=None) -> None:
        super().__init__(parent)
        self.fix = fix
        self.result = result
        card = make_card()
        card.setProperty("cardHover", "true")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.title_label = QLabel(fix.title_for(i18n.language))
        self.title_label.setObjectName("cardTitle")
        self.problem_label = QLabel(result.summary_for(i18n.language))
        self.problem_label.setWordWrap(True)
        self.problem_label.setObjectName("muted")
        self.action_label = QLabel(fix.description_for(i18n.language))
        self.action_label.setWordWrap(True)
        self.status_label = QLabel("")
        self.status_label.setObjectName("cardStatus")

        self.btn_fix = AnimatedButton(variant="primary", icon_name="wrench")
        self.btn_skip = AnimatedButton(variant="ghost", icon_name="cross")
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.btn_skip)
        buttons.addWidget(self.btn_fix)

        layout.addWidget(self.title_label)
        layout.addWidget(self.problem_label)
        layout.addWidget(self.action_label)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self.retranslate_ui()

    def set_state(self, state: str, message: str = "") -> None:
        colors = {"fixed": "#00ff88", "failed": "#ff4757", "skipped": "#98a2c8", "running": "#9146ff"}
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {colors.get(state, '#98a2c8')};")
        self.btn_fix.setEnabled(False)
        self.btn_skip.setEnabled(False)

    def retranslate_ui(self) -> None:
        self.title_label.setText(self.fix.title_for(i18n.language))
        self.problem_label.setText(self.result.summary_for(i18n.language))
        self.action_label.setText(self.fix.description_for(i18n.language))
        self.btn_fix.setText(i18n.tr("common.fix"))
        self.btn_skip.setText(i18n.tr("common.skip"))


class AutofixPage(BasePage):
    """Список найденных проблем и управление исправлениями."""

    apply_fixes = pyqtSignal(list, dict, bool)  # ids, context, restore_point
    quick_fix = pyqtSignal(bool)
    restart_admin = pyqtSignal()
    message = pyqtSignal(str, str)

    def __init__(self, settings: Any, parent=None) -> None:
        super().__init__("autofix.title", "autofix.subtitle", parent)
        self.settings = settings
        self.cards: dict[str, ProblemCard] = {}
        self.context: dict[str, dict[str, Any]] = {}
        self.results: list[CheckResult] = []
        self._running = False

        # Баннер про UAC.
        self.admin_banner = make_card("bannerCard")
        banner_layout = QHBoxLayout(self.admin_banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)
        banner_layout.setSpacing(10)
        self.admin_label = QLabel()
        self.admin_label.setWordWrap(True)
        self.btn_admin = AnimatedButton(variant="secondary", icon_name="shield")
        self.btn_admin.clicked.connect(self.restart_admin)
        banner_layout.addWidget(self.admin_label, 1)
        banner_layout.addWidget(self.btn_admin)
        self.banner_layout = banner_layout
        self.add_content(self.admin_banner)

        # Настройки бэкапа + Quick Fix.
        options_card = make_card()
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(16, 12, 16, 12)
        options_layout.setSpacing(8)
        self.restore_checkbox = QCheckBox()
        self.restore_checkbox.setChecked(bool(settings.get("restore_point")))
        self.restore_checkbox.toggled.connect(lambda value: settings.set("restore_point", bool(value)))
        self.backup_note = QLabel()
        self.backup_note.setObjectName("muted")
        self.backup_note.setWordWrap(True)
        self.btn_quick = AnimatedButton(variant="ghost", icon_name="rocket")
        self.btn_quick.clicked.connect(lambda: self.quick_fix.emit(self.restore_checkbox.isChecked()))
        options_layout.addWidget(self.restore_checkbox)
        options_layout.addWidget(self.backup_note)
        options_layout.addWidget(self.btn_quick, 0, Qt.AlignmentFlag.AlignLeft)
        self.add_content(options_card)

        # Карточки проблем.
        self.problems_widget = QWidget()
        self.problems_layout = QVBoxLayout(self.problems_widget)
        self.problems_layout.setContentsMargins(0, 0, 0, 0)
        self.problems_layout.setSpacing(10)
        self.add_content(self.problems_widget)
        self.empty_label = QLabel()
        self.empty_label.setObjectName("muted")
        self.empty_label.setWordWrap(True)
        self.add_content(self.empty_label)

        # Кнопка «Исправить всё» + прогресс.
        bottom_card = make_card()
        bottom_layout = QVBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.setSpacing(10)
        self.progress = GradientProgressBar()
        self.btn_fix_all = AnimatedButton(variant="primary", icon_name="wrench")
        self.btn_fix_all.clicked.connect(self._fix_all)
        bottom_layout.addWidget(self.progress)
        bottom_layout.addWidget(self.btn_fix_all)
        self.add_content(bottom_card)
        self.set_results([])
        self.retranslate_ui()

    # --------------------------------------------------------------- данные
    def set_results(self, results: list[CheckResult]) -> None:
        """Перестроить список карточек по результатам диагностики."""
        self.results = results
        self.cards.clear()
        self.context.clear()
        while self.problems_layout.count():
            item = self.problems_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        fixes = fixes_for_results(results)
        self.context = {
            result.fix_id: result.data
            for result in reversed(results)
            if result.is_problem and result.fix_id
        }
        for fix in fixes:
            problem = next(
                (item for item in results if item.fix_id == fix.id and item.is_problem), None
            )
            if problem is None:
                continue
            card = ProblemCard(fix, problem)
            card.btn_fix.clicked.connect(lambda checked=False, f=fix: self._fix_one(f))
            card.btn_skip.clicked.connect(lambda checked=False, f=fix: self._skip(f.id))
            self.problems_layout.addWidget(card)
            self.cards[fix.id] = card
        self.empty_label.setVisible(not bool(fixes))
        self.btn_fix_all.setEnabled(bool(fixes))
        self.problems_widget.setVisible(bool(fixes))

    def set_admin(self, is_admin: bool) -> None:
        self.admin_banner.setVisible(not is_admin)

    def set_running(self, running: bool) -> None:
        self._running = running
        self.btn_fix_all.setEnabled(not running and bool(self.cards))
        self.btn_quick.setEnabled(not running)
        for card in self.cards.values():
            card.btn_fix.setEnabled(not running)
            card.btn_skip.setEnabled(not running)

    def on_progress(self, done: int, total: int, label: str) -> None:
        if label != "done":
            for card in self.cards.values():
                if card.fix.title_ru == label or card.fix.title_en == label:
                    card.set_state("running", i18n.tr("autofix.running"))
        self.progress.setValue(int(done / max(1, total) * 100))

    def on_fix_result(self, result: FixResult) -> None:
        card = self.cards.get(result.fix_id)
        if card:
            state = "fixed" if result.success else "failed"
            card.set_state(state, f"{i18n.tr('autofix.fixed' if result.success else 'common.failed')}: {result.message}")
        level = "ok" if result.success else "err"
        self.message.emit(
            f"{result.fix_id}: {result.message if i18n.language == 'ru' else result.message_en}", level
        )

    def on_finished(self, results: list[FixResult]) -> None:
        self.set_running(False)
        self.progress.setValue(100)
        successes = sum(1 for item in results if item.success)
        self.message.emit(f"{i18n.tr('common.done')}: {successes}/{len(results)}", "ok")

    # ------------------------------------------------------------- действия
    def _confirm(self, text: str) -> bool:
        answer = QMessageBox.question(
            self,
            i18n.tr("autofix.confirm_title"),
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _fix_one(self, fix: BaseFix) -> None:
        if fix.requires_admin and not self._admin_ok():
            return
        if not self._confirm(i18n.tr("autofix.confirm_text", fix.title_for(i18n.language))):
            return
        self.apply_fixes.emit([fix.id], {fix.id: self.context.get(fix.id, {})}, self.restore_checkbox.isChecked())

    def _fix_all(self) -> None:
        ids = list(self.cards)
        if not ids:
            return
        if any(card.fix.requires_admin for card in self.cards.values()) and not self._admin_ok():
            return
        if not self._confirm(i18n.tr("autofix.confirm_all", len(ids))):
            return
        self.apply_fixes.emit(ids, dict(self.context), self.restore_checkbox.isChecked())

    def _skip(self, fix_id: str) -> None:
        card = self.cards.get(fix_id)
        if card:
            card.set_state("skipped", i18n.tr("autofix.skipped"))

    def _admin_ok(self) -> bool:
        from src.utils.admin import is_admin  # noqa: PLC0415

        if is_admin():
            return True
        self.message.emit(i18n.tr("autofix.need_admin"), "warn")
        self.restart_admin.emit()
        return False

    def set_narrow(self, narrow: bool) -> None:
        from PyQt6.QtWidgets import QBoxLayout  # noqa: PLC0415

        super().set_narrow(narrow)
        self.banner_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        )

    # --------------------------------------------------------- локализация
    def retranslate_ui(self) -> None:
        super().retranslate_ui()
        self.admin_label.setText(i18n.tr("autofix.admin_banner"))
        self.btn_admin.setText(i18n.tr("common.restart_admin"))
        self.restore_checkbox.setText(i18n.tr("autofix.restore_point"))
        self.backup_note.setText(i18n.tr("autofix.backup_note"))
        self.btn_quick.setText(i18n.tr("common.quick_fix"))
        self.btn_fix_all.setText(i18n.tr("common.fix_all"))
        self.empty_label.setText(i18n.tr("autofix.no_problems_hint"))
        for card in self.cards.values():
            card.retranslate_ui()
