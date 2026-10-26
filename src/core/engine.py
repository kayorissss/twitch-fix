"""Асинхронные движки диагностики и исправлений (QThreadPool + сигналы).

UI-поток никогда не выполняет сетевые запросы: каждая проверка — QRunnable
в пуле, результаты приходят через Qt-сигналы (автоматическая queued delivery).
"""
from __future__ import annotations

import threading
from typing import Any

from PyQt6.QtCore import QObject, QThreadPool, QRunnable, pyqtSignal

from src.core.diagnostics import all_checks
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.core.fixes import fix_by_id
from src.core.fixes.base_fix import BaseFix, FixResult
from src.core.fixes.quick_fix import QuickFix
from src.utils.backup import BackupManager
from src.utils.logger import get_logger

log = get_logger(__name__)


class _Signals(QObject):
    """Выделенный QObject-владелец сигналов (QRunnable не наследует QObject)."""

    started = pyqtSignal(object)          # list[CheckResult] в статусе RUNNING
    check_started = pyqtSignal(str)       # check id
    check_finished = pyqtSignal(object)   # CheckResult
    fix_finished = pyqtSignal(object)     # FixResult
    progress = pyqtSignal(int, int, str)  # done, total, label
    log = pyqtSignal(str, str)            # level, message
    finished = pyqtSignal(object)         # list результатов


class _CheckTask(QRunnable):
    def __init__(self, check: BaseCheck, signals: _Signals) -> None:
        super().__init__()
        self.check = check
        self.signals = signals

    def run(self) -> None:
        self.signals.check_started.emit(self.check.id)
        result = self.check.safe_run()
        self.signals.check_finished.emit(result)


class DiagnosticEngine(QObject):
    """Запускает 13 проверок параллельно и собирает результаты."""

    started = pyqtSignal(object)
    check_started = pyqtSignal(str)
    check_finished = pyqtSignal(object)
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str, str)
    finished = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None, max_workers: int = 4) -> None:
        super().__init__(parent)
        self.signals = _Signals()
        self.signals.started.connect(self.started)
        self.signals.check_started.connect(self.check_started)
        self.signals.check_finished.connect(self._on_check_finished)
        self.signals.progress.connect(self.progress)
        self.signals.log.connect(self.log)
        self.signals.finished.connect(self.finished)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(max_workers)
        self._cancel = threading.Event()
        self._tasks: list[_CheckTask] = []
        self._results: list[CheckResult] = []
        self._pending: set[str] = set()
        self._total = 0
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return False
        self._cancel.clear()
        checks = all_checks(cancelled=self._cancel.is_set)
        self._total = len(checks)
        self._results = []
        self._running = True
        self._tasks = [_CheckTask(check, self.signals) for check in checks]
        self._pending = {check.id for check in checks}
        pending = [
            CheckResult(
                id=check.id,
                title=check.title_ru,
                title_en=check.title_en,
                status=Status.RUNNING,
                summary="",
                summary_en="",
            )
            for check in checks
        ]
        self.signals.started.emit(pending)
        self.signals.log.emit("info", f"Diagnostics started: {self._total} checks")
        for task in self._tasks:
            self.pool.start(task)
        return True

    def stop(self) -> None:
        """Мягкая отмена: длинные проверки проверяют флаг между шагами.

        Очередь очищается, а незапущенные проверки помечаются SKIPPED —
        движок всегда корректно завершает сессию и уведомляет UI.
        """
        if not self._running:
            return
        self._cancel.set()
        self.pool.clear()
        self.signals.log.emit("warn", "Diagnostics cancellation requested")
        for check_id in sorted(self._pending):
            self._on_check_finished(
                CheckResult(
                    id=check_id,
                    title=check_id,
                    title_en=check_id,
                    status=Status.SKIPPED,
                    summary="Проверка отменена",
                    summary_en="Check cancelled",
                    fix_id=None,
                )
            )

    def _on_check_finished(self, result: CheckResult) -> None:
        if result.id not in self._pending:
            return  # поздний результат уже отменённой проверки — игнорируем
        self._pending.discard(result.id)
        self._results.append(result)
        level = {"ok": "ok", "warning": "warn", "error": "err"}.get(result.status.value, "info")
        self.signals.log.emit(level, f"[{result.title}] {result.summary}")
        self.signals.progress.emit(len(self._results), self._total, result.title)
        self.signals.check_finished.emit(result)
        if not self._pending:
            self._running = False
            self._tasks.clear()
            self.signals.log.emit("ok", f"Diagnostics finished: {len(self._results)} results")
            self.signals.finished.emit(list(self._results))


class _FixTask(QRunnable):
    """Последовательно применяет исправления в одном worker-потоке."""

    def __init__(
        self,
        engine: "FixEngine",
        fix_ids: list[str],
        context: dict[str, dict[str, Any]],
        restore_point: bool,
        dry_run: bool,
        quick: bool,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.fix_ids = fix_ids
        self.context = context
        self.restore_point = restore_point
        self.dry_run = dry_run
        self.quick = quick

    def run(self) -> None:
        signals = self.engine.signals
        backup = BackupManager()
        if self.restore_point and not self.dry_run:
            signals.progress.emit(0, max(1, len(self.fix_ids)), "restore point")
            signals.log.emit("info", "Creating Windows restore point (may take a while)…")
            backup.create_restore_point()

        results: list[FixResult] = []
        if self.quick:
            fix = QuickFix(
                backup=backup,
                on_step=lambda title, index, total: (
                    signals.progress.emit(index, total, title),
                    signals.log.emit("info", f"Quick Fix step {index}/{total}: {title}"),
                ),
            )
            outcome = fix.safe_apply(dry_run=self.dry_run)
            signals.fix_finished.emit(outcome)
            results.append(outcome)
        else:
            total = max(1, len(self.fix_ids))
            for index, fix_id in enumerate(self.fix_ids, start=1):
                if self.engine.cancelled:
                    signals.log.emit("warn", "Fix sequence cancelled")
                    break
                cls = fix_by_id(fix_id)
                if cls is None:
                    continue
                instance: BaseFix = cls(backup=backup)
                instance.context = self.context.get(fix_id, {})
                signals.progress.emit(index - 1, total, instance.title_ru)
                outcome = instance.safe_apply(dry_run=self.dry_run)
                results.append(outcome)
                signals.fix_finished.emit(outcome)
                signals.progress.emit(index, total, instance.title_ru)
                signals.log.emit(
                    "ok" if outcome.success else "err", f"{instance.title_ru}: {outcome.message}"
                )
                for detail in outcome.details:
                    signals.log.emit("debug", f"    {detail}")
        signals.progress.emit(1, 1, "done")
        signals.finished.emit(results)


class FixEngine(QObject):
    """Движок исправлений: бэкап-сессия, точка восстановления, прогресс."""

    progress = pyqtSignal(int, int, str)
    fix_finished = pyqtSignal(object)
    log = pyqtSignal(str, str)
    finished = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.signals = _Signals()
        self.signals.progress.connect(self.progress)
        self.signals.fix_finished.connect(self.fix_finished)
        self.signals.log.connect(self.log)
        self.signals.finished.connect(self.finished)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.cancelled = False
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def apply(
        self,
        fix_ids: list[str],
        context: dict[str, dict[str, Any]] | None = None,
        restore_point: bool = True,
        dry_run: bool = False,
    ) -> bool:
        if self._running:
            return False
        self._running = True
        self.cancelled = False
        task = _FixTask(self, fix_ids, context or {}, restore_point, dry_run, quick=False)
        self.signals.finished.connect(self._done)
        self.pool.start(task)
        return True

    def quick_fix(self, restore_point: bool = True, dry_run: bool = False) -> bool:
        if self._running:
            return False
        self._running = True
        self.cancelled = False
        task = _FixTask(self, [], {}, restore_point, dry_run, quick=True)
        self.signals.finished.connect(self._done)
        self.pool.start(task)
        return True

    def cancel(self) -> None:
        self.cancelled = True

    def _done(self, _results: object) -> None:
        self._running = False
        try:
            self.signals.finished.disconnect(self._done)
        except TypeError:
            pass
