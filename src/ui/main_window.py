"""Главное frameless-окно TwitchFix.

Собирает title bar, sidebar, пять страниц, асинхронные движки, фоновый
мониторинг и системный трей. Реализует перетаскивание, resize handles,
компактный/полноэкранный режим и плавные переходы между экранами.
"""
from __future__ import annotations

import sys
from typing import Any

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.constants import (
    APP_NAME,
    APP_VERSION,
    COMPACT_HEIGHT,
    COMPACT_WIDTH,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from src.config.i18n import i18n
from src.core.diagnostics.base_check import CheckResult, Status, overall_status
from src.core.engine import DiagnosticEngine, FixEngine
from src.core.fixes.base_fix import FixResult
from src.core.history import History
from src.core.monitor import Monitor
from src.core.report_generator import ReportGenerator
from src.ui import theme as theme_module
from src.ui.icons import app_icon
from src.ui.pages.autofix import AutofixPage
from src.ui.pages.dashboard import DashboardPage
from src.ui.pages.diagnostics import DiagnosticsPage
from src.ui.pages.report import ReportPage
from src.ui.pages.settings import SettingsPage
from src.ui.sidebar import Sidebar
from src.ui.title_bar import TitleBar
from src.ui.tray import TrayManager
from src.ui.widgets.toast_notification import ToastManager
from src.utils.admin import is_admin, relaunch_with_admin
from src.utils.logger import get_logger
from src.utils.paths import app_dirs

log = get_logger(__name__)
EDGE_MARGIN = 8


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget с fade-out/fade-in и лёгким slide при переключении.

    Эффекты прозрачности создаются только на время анимации и сразу
    удаляются: постоянный QGraphicsEffect на странице со скролл-областями
    может сдвинуть содержимое при отрисовке.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._animating = False

    def switch_to(self, index: int) -> None:
        if index == self.currentIndex() or self._animating or not (0 <= index < self.count()):
            return
        self._animating = True
        old = self.currentWidget()
        target = self.widget(index)
        old_effect = QGraphicsOpacityEffect(old)
        new_effect = QGraphicsOpacityEffect(target)
        old_effect.setOpacity(1.0)
        new_effect.setOpacity(0.0)
        old.setGraphicsEffect(old_effect)
        target.setGraphicsEffect(new_effect)

        group = QSequentialAnimationGroup(self)
        fade_out = QPropertyAnimation(old_effect, b"opacity", group)
        fade_out.setDuration(110)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(fade_out)
        fade_in = QPropertyAnimation(new_effect, b"opacity", group)
        fade_in.setDuration(210)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(fade_in)
        start_pos = target.pos()

        def begin_fade_in() -> None:
            self.setCurrentIndex(index)
            old_effect.setOpacity(1.0)
            target.move(start_pos.__class__(start_pos.x() + 18, start_pos.y()))
            slide = QPropertyAnimation(target, b"pos", target)
            slide.setDuration(200)
            slide.setEndValue(start_pos)
            slide.setEasingCurve(QEasingCurve.Type.OutCubic)
            setattr(target, "_slide_animation", slide)
            slide.start()

        fade_out.finished.connect(begin_fade_in)

        def cleanup() -> None:
            old.setGraphicsEffect(None)
            target.setGraphicsEffect(None)
            target.move(start_pos)
            self._animating = False

        group.finished.connect(cleanup)
        setattr(self, "_switch_animation", group)
        group.start()


class MainWindow(QWidget):
    """Главное окно приложения."""

    closed = pyqtSignal()

    def __init__(self, settings: Any, history: History | None = None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.history = history or History(retention_days=int(settings.get("history_days")))
        self.results: list[CheckResult] = []
        self.fix_results: list[FixResult] = []
        self._force_quit = False
        self._maximized = False
        self._fullscreen = False
        self._resize_edge: Qt.Edges | None = None
        self._drag_origin: QPoint | None = None
        self._drag_size = None
        self._auto_compact = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMouseTracking(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)
        self.container = QFrame()
        self.container.setObjectName("windowContainer")
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)
        outer.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        self.title_bar = TitleBar(self.container)
        container_layout.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = Sidebar(self.container, expanded=True)
        body.addWidget(self.sidebar)
        self.stack = AnimatedStackedWidget(self.container)
        self.stack.setObjectName("contentArea")
        body.addWidget(self.stack, 1)
        container_layout.addLayout(body, 1)

        footer = QFrame()
        footer.setFixedHeight(26)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 0, 6, 0)
        self.footer_label = QLabel(f"{APP_NAME} v{APP_VERSION}  •  {i18n.tr('app.subtitle')}")
        self.footer_label.setObjectName("muted")
        footer_layout.addWidget(self.footer_label, 1)
        self.monitor_label = QLabel("")
        self.monitor_label.setObjectName("muted")
        footer_layout.addWidget(self.monitor_label)
        grip = QSizeGrip(footer)
        footer_layout.addWidget(grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        container_layout.addWidget(footer)

        # Страницы.
        self.dashboard = DashboardPage(self.history, self.stack)
        self.diagnostics = DiagnosticsPage(self.stack)
        self.autofix = AutofixPage(self.settings, self.stack)
        self.report = ReportPage(self.history, self.stack)
        self.settings_page = SettingsPage(self.settings, self.stack)
        for page in (
            self.dashboard, self.diagnostics, self.autofix, self.report, self.settings_page
        ):
            self.stack.addWidget(page)
        self.stack.setCurrentIndex(0)

        # Движки, мониторинг, трей, уведомления.
        self.diag_engine = DiagnosticEngine(self)
        self.fix_engine = FixEngine(self)
        self.monitor = Monitor(self.settings, self.history, self)
        self.toasts = ToastManager(self)
        self.tray: TrayManager | None = None
        if TrayManager.is_available():
            try:
                self.tray = TrayManager(self, bool(self.settings.get("notifications")))
            except Exception as exc:
                log.warning("Tray unavailable: %s", exc)

        self.autofix.set_admin(is_admin())
        self._wire_signals()
        i18n.set_language(str(self.settings.get("language")))
        theme_module.load_theme(str(self.settings.get("theme")))
        self._refresh_icons()
        self.retranslate_all()
        if self.settings.get("monitoring"):
            self.monitor.start()
        if self.settings.get("compact"):
            self.set_compact(True)
        self._restore_geometry()

    # ------------------------------------------------------------- сигналы
    def _wire_signals(self) -> None:
        tb = self.title_bar
        tb.minimize_clicked.connect(self.showMinimized)
        tb.maximize_clicked.connect(self.toggle_maximize)
        tb.compact_clicked.connect(lambda: self.set_compact(not self.settings.get("compact")))
        tb.close_clicked.connect(self.close)
        self.sidebar.page_changed.connect(self.navigate)
        i18n.language_changed.connect(lambda _lang: self.retranslate_all())

        # Dashboard.
        self.dashboard.run_diagnostics.connect(self.start_diagnostics)
        self.dashboard.quick_fix.connect(lambda: self.run_quick_fix(bool(self.settings.get("restore_point"))))
        self.dashboard.open_report.connect(lambda: self.navigate(3))
        self.dashboard.card_clicked.connect(self.open_check_details)
        self.dashboard.message.connect(self.show_message)

        # Diagnostics.
        self.diagnostics.start_requested.connect(self.start_diagnostics)
        self.diagnostics.stop_requested.connect(self.stop_diagnostics)
        self.diagnostics.open_report.connect(lambda: self.navigate(3))
        self.diagnostics.message.connect(self.show_message)

        # Auto-fix.
        self.autofix.apply_fixes.connect(self.apply_fixes)
        self.autofix.quick_fix.connect(self.run_quick_fix)
        self.autofix.restart_admin.connect(self.restart_as_admin)
        self.autofix.message.connect(self.show_message)

        # Report / Settings.
        self.report.message.connect(self.show_message)
        self.settings_page.theme_changed.connect(self.change_theme)
        self.settings_page.language_changed.connect(self.change_language)
        self.settings_page.settings_changed.connect(self.on_setting_changed)
        self.settings_page.open_logs.connect(self.open_logs_folder)
        self.settings_page.reset_settings.connect(self.reset_settings)

        # Движок диагностики.
        self.diag_engine.started.connect(self.diagnostics.on_started)
        self.diag_engine.check_started.connect(self.diagnostics.on_check_started)
        self.diag_engine.check_finished.connect(self.diagnostics.on_check_finished)
        self.diag_engine.progress.connect(self.diagnostics.on_progress)
        self.diag_engine.log.connect(self.diagnostics.append_log)
        self.diag_engine.finished.connect(self.on_diagnostics_finished)

        # Движок исправлений.
        self.fix_engine.progress.connect(self.autofix.on_progress)
        self.fix_engine.fix_finished.connect(self.on_fix_finished)
        self.fix_engine.log.connect(lambda level, text: self.diagnostics.append_log(level, text))
        self.fix_engine.finished.connect(self.on_fixes_finished)

        # Мониторинг/трей.
        self.monitor.checked.connect(self.on_monitor_checked)
        self.monitor.state_changed.connect(self.on_monitor_state_changed)
        self.monitor.log.connect(lambda level, text: log.info("%s %s", level, text))
        if self.tray:
            self.tray.show_window.connect(self.show_window)
            self.tray.check_now.connect(self.monitor.check_now)
            self.tray.quit_app.connect(self.quit_app)

    # ----------------------------------------------------------- навигация
    @pyqtSlot(int)
    def navigate(self, index: int) -> None:
        self.sidebar.set_active(index)
        self.stack.switch_to(index)

    def open_check_details(self, check_id: str) -> None:
        self.navigate(1)
        self.diagnostics.expand_check(check_id)

    def show_window(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_maximize(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self._fullscreen = False
        elif self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.title_bar.set_maximized(self.isMaximized())

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self._fullscreen = False
            self.layout().setContentsMargins(12, 12, 12, 12)
        else:
            self.showFullScreen()
            self._fullscreen = True
            self.layout().setContentsMargins(0, 0, 0, 0)
        self.title_bar.set_maximized(self.isFullScreen())

    def set_compact(self, compact: bool) -> None:
        self.settings.set("compact", bool(compact))
        if self.sidebar.is_expanded == compact:
            self.sidebar.toggle()
        if compact:
            self.showNormal()
            self.resize(COMPACT_WIDTH, COMPACT_HEIGHT)
            self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
            self.sidebar.set_expanded(False, animate=False)
            self.title_bar.set_compact(True)
            self._auto_compact = True
        else:
            self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
            self.sidebar.set_expanded(True, animate=False)
            self.title_bar.set_compact(False)
            self._auto_compact = False
        for page in (self.dashboard, self.diagnostics, self.autofix, self.report, self.settings_page):
            page.set_narrow(compact)
        self.toasts.show(
            i18n.tr("title.compact") if compact else i18n.tr("title.fullscreen"), "info"
        )

    # ------------------------------------------------------ диагностика
    def start_diagnostics(self) -> None:
        if self.diag_engine.is_running:
            return
        self.navigate(1)
        self.dashboard.set_checking(True)
        if not self.diag_engine.start():
            self.dashboard.set_checking(False)

    def stop_diagnostics(self) -> None:
        self.diag_engine.stop()

    def on_diagnostics_finished(self, results: list[CheckResult]) -> None:
        self.results = results
        self.dashboard.set_checking(False)
        self.dashboard.set_results(results)
        self.autofix.set_results(results)
        self.history.add_results(results)
        self.dashboard.update_chart()
        self.refresh_report()
        status = overall_status(results)
        if self.tray:
            self.tray.set_status(status == Status.OK, i18n.tr("monitor.check_ok"))
        problems = [item for item in results if item.is_problem]
        self.show_message(
            f"{i18n.tr('common.done')}: {len(results)} • {i18n.tr('report.issues', len(problems))}",
            "warn" if problems else "ok",
        )

    # ---------------------------------------------------------- исправления
    @pyqtSlot(list, dict, bool)
    def apply_fixes(self, fix_ids: list[str], context: dict, restore_point: bool) -> None:
        if self.fix_engine.is_running:
            return
        from src.core.fixes import fix_by_id  # noqa: PLC0415

        needs_admin = any(
            (cls := fix_by_id(fix_id)) and cls.requires_admin for fix_id in fix_ids
        )
        if needs_admin and not is_admin():
            self.show_message(i18n.tr("autofix.need_admin"), "warn")
            self.autofix.set_admin(False)
            return
        self.autofix.set_running(True)
        self.autofix.progress.setValue(0, animate=False)
        self.fix_engine.apply(fix_ids, context, restore_point=restore_point)

    @pyqtSlot(bool)
    def run_quick_fix(self, restore_point: bool = True) -> None:
        if self.fix_engine.is_running:
            return
        if not is_admin():
            self.show_message(i18n.tr("autofix.need_admin"), "warn")
            self.autofix.set_admin(False)
            return
        self.autofix.set_running(True)
        self.autofix.progress.setValue(0, animate=False)
        self.show_message(i18n.tr("autofix.quick_running"), "info")
        self.fix_engine.quick_fix(restore_point=restore_point)

    def on_fix_finished(self, result: FixResult) -> None:
        self.fix_results.append(result)
        self.autofix.on_fix_result(result)
        self.refresh_report()

    def on_fixes_finished(self, results: list[FixResult]) -> None:
        self.autofix.on_finished(results)
        self.show_message(i18n.tr("autofix.quick_done") if any(r.fix_id == "quick" for r in results)
                          else f"{i18n.tr('common.done')}: {len(results)}", "ok")

    # --------------------------------------------------------------- отчёт
    def refresh_report(self) -> None:
        if not self.results:
            return
        generator = ReportGenerator(
            results=self.results,
            fixes=self.fix_results,
            history=self.history,
            language=i18n.language,
        )
        self.report.set_report(generator)

    # ------------------------------------------------------------ настройки
    def change_theme(self, name: str) -> None:
        theme_module.load_theme(name)
        self._refresh_icons()

    def change_language(self, language: str) -> None:
        i18n.set_language(language)

    def on_setting_changed(self, key: str, value: object) -> None:
        from src.utils.autostart import set_enabled  # noqa: PLC0415

        if key == "autostart":
            if not set_enabled(bool(value)) and sys.platform == "win32":
                self.show_message("Cannot change autostart (registry error)", "warn")
        elif key == "monitoring":
            self.monitor.apply_settings()
        elif key == "monitor_interval":
            if self.settings.get("monitoring"):
                self.monitor.start()
        elif key == "notifications" and self.tray:
            self.tray.set_notifications(bool(value))
        elif key == "history_days":
            self.history.retention_days = max(1, int(value))
            self.history.prune()
            self.dashboard.update_chart()

    def reset_settings(self) -> None:
        self.settings.reset()
        self.settings_page.sync_from_settings()
        i18n.set_language(str(self.settings.get("language")))
        theme_module.load_theme(str(self.settings.get("theme")))
        self._refresh_icons()
        self.retranslate_all()
        self.show_message(i18n.tr("common.saved"), "ok")

    def open_logs_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_dirs().logs)))

    def restart_as_admin(self) -> None:
        if is_admin():
            self.show_message(i18n.tr("common.admin_required") + ": OK", "ok")
            return
        if not relaunch_with_admin():
            self.show_message(i18n.tr("common.admin_required"), "warn")

    # ------------------------------------------------------------ мониторинг
    def on_monitor_checked(self, ok: bool, message: str) -> None:
        self.monitor_label.setText(("● " if ok else "● ") + message)
        self.monitor_label.setStyleSheet(f"color: {theme_module.status_color('ok' if ok else 'error')};")
        if self.tray:
            self.tray.set_status(ok, message)

    def on_monitor_state_changed(self, ok: bool, message: str) -> None:
        if not self.settings.get("notifications"):
            return
        title = i18n.tr("monitor.up_title" if ok else "monitor.down_title")
        body = i18n.tr("monitor.up_msg" if ok else "monitor.down_msg")
        if self.tray:
            self.tray.notify(title, body, "ok" if ok else "err")
        self.show_message(f"{title}: {message}", "ok" if ok else "err")

    # --------------------------------------------------------------- трей
    def quit_app(self) -> None:
        self._force_quit = True
        self.monitor.stop()
        QApplication.instance().quit() if QApplication.instance() else None

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_geometry()
        if self.tray and self.settings.get("notifications") and not self._force_quit:
            event.ignore()
            self.hide()
            self.tray.notify(
                APP_NAME,
                "TwitchFix continues monitoring in the tray. "
                + i18n.tr("common.close_app")
                + " — tray menu → Quit.",
                "info",
            )
        else:
            self.monitor.stop()
            event.accept()
            self.closed.emit()

    def _save_geometry(self) -> None:
        try:
            self.settings.set("geometry", f"{self.width()}x{self.height()}+{self.x()}+{self.y()}")
        except Exception as exc:
            log.warning("Cannot save geometry: %s", exc)

    def _restore_geometry(self) -> None:
        value = str(self.settings.get("geometry") or "")
        try:
            size, x, y = value.split("+")[0], *value.split("+")[1:]
            width, height = (int(part) for part in size.split("x"))
            if width >= WINDOW_MIN_WIDTH and height >= WINDOW_MIN_HEIGHT:
                self.resize(width, height)
                self.move(int(x), int(y))
        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------- локализация
    def _refresh_icons(self) -> None:
        self.title_bar.refresh_icons()
        self.sidebar.refresh_icons()
        self.dashboard.hero.refresh_icon()
        for card in self.dashboard.cards.values():
            card.refresh_icon()

    def retranslate_all(self) -> None:
        self.title_bar.retranslate_ui()
        self.sidebar.retranslate_ui()
        for page in (
            self.dashboard, self.diagnostics, self.autofix, self.report, self.settings_page
        ):
            page.retranslate_ui()
        self.autofix.set_results(self.results)
        self.footer_label.setText(f"{APP_NAME} v{APP_VERSION}  •  {i18n.tr('app.subtitle')}")
        if self.tray:
            self.tray.retranslate_ui()
        self.refresh_report()

    # ------------------------------------------------------------- события
    def _edges_at(self, position: QPoint) -> Qt.Edges:
        """Определить, за какой край окна тянет пользователь."""
        edges = Qt.Edges(Qt.Edge(0))
        rect = self.rect()
        if position.x() <= EDGE_MARGIN:
            edges |= Qt.Edge.LeftEdge
        if position.x() >= rect.width() - EDGE_MARGIN:
            edges |= Qt.Edge.RightEdge
        if position.y() <= EDGE_MARGIN:
            edges |= Qt.Edge.TopEdge
        if position.y() >= rect.height() - EDGE_MARGIN:
            edges |= Qt.Edge.BottomEdge
        return edges

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._edges_at(event.position().toPoint())
            if edges:
                self._resize_edge = edges
                handle = self.windowHandle()
                if handle is not None and hasattr(handle, "startSystemResize"):
                    try:
                        if handle.startSystemResize(edges):
                            return
                    except Exception:
                        pass
                self._drag_origin = event.globalPosition().toPoint()
                self._drag_size = self.size()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        position = event.position().toPoint()
        edges = self._edges_at(position)
        if edges and not self._resize_edge:
            horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
            vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor if horizontal and vertical
                else Qt.CursorShape.SizeHorCursor if horizontal
                else Qt.CursorShape.SizeVerCursor
            )
        elif not self._resize_edge:
            self.unsetCursor()

        if self._resize_edge and self._drag_origin and self._drag_size:
            delta = event.globalPosition().toPoint() - self._drag_origin
            width = self._drag_size.width()
            height = self._drag_size.height()
            x, y = self.x(), self.y()
            if self._resize_edge & Qt.Edge.RightEdge:
                width = max(self.minimumWidth(), width + delta.x())
            if self._resize_edge & Qt.Edge.BottomEdge:
                height = max(self.minimumHeight(), height + delta.y())
            if self._resize_edge & Qt.Edge.LeftEdge:
                width = max(self.minimumWidth(), width - delta.x())
                x += delta.x()
            if self._resize_edge & Qt.Edge.TopEdge:
                height = max(self.minimumHeight(), height - delta.y())
                y += delta.y()
            self.setGeometry(x, y, width, height)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._resize_edge = None
        self._drag_origin = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Автоматически сворачивать sidebar/title bar в узком окне."""
        super().resizeEvent(event)
        if not hasattr(self, "dashboard"):
            return
        narrow = self.width() < 700
        if narrow == self._auto_compact:
            return
        self._auto_compact = narrow
        if narrow and self.sidebar.is_expanded:
            self.sidebar.set_expanded(False, animate=False)
        elif not narrow and not self.sidebar.is_expanded and not self.settings.get("compact"):
            self.sidebar.set_expanded(True, animate=False)
        self.title_bar.set_compact(narrow)
        for page in (self.dashboard, self.diagnostics, self.autofix, self.report, self.settings_page):
            page.set_narrow(narrow)

    def changeEvent(self, event) -> None:  # type: ignore[override]
        if event.type() == QEvent.Type.WindowStateChange:
            self.title_bar.set_maximized(self.isMaximized() or self.isFullScreen())
        super().changeEvent(event)

    def show_message(self, message: str, level: str = "info") -> None:
        self.toasts.show(message, level)

    def set_demo_results(self, results: list[CheckResult]) -> None:
        """Подставить демонстрационные данные (используется генератором скриншотов)."""
        self.results = results
        self.dashboard.set_results(results)
        self.diagnostics.on_started([])
        for result in results:
            self.diagnostics.on_check_finished(result)
        self.diagnostics.on_progress(len(results), len(results), "demo")
        self.autofix.set_results(results)
        self.refresh_report()
