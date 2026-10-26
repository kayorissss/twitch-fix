"""Асинхронные движки: проверки в QThreadPool и последовательность исправлений."""
from __future__ import annotations

import pytest

QtCore = pytest.importorskip("PyQt6.QtCore")
from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer  # noqa: E402

from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status  # noqa: E402
from src.core.engine import DiagnosticEngine, FixEngine  # noqa: E402
from src.core.fixes.base_fix import BaseFix, FixResult  # noqa: E402


class DummyCheck(BaseCheck):
    id = "dummy"
    title_ru = "Тест"
    title_en = "Test"

    def run(self) -> CheckResult:
        return self.result(Status.OK, "ok", "ok", details=["fast"])


class DummyFix(BaseFix):
    id = "dummy_fix"
    title_ru = "Тест"
    title_en = "Test"
    requires_admin = False

    def apply(self, dry_run: bool = False) -> FixResult:
        return self.result(True, "ok", "ok", details=["dry" if dry_run else "applied"])


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def wait_for(signal, timeout_ms: int = 5000) -> object:
    loop = QEventLoop()
    captured: list[object] = []
    signal.connect(lambda *args: (captured.append(args), loop.quit()))
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    assert captured, "signal was not emitted before timeout"
    return captured[0]


def test_diagnostic_engine_start_then_wait(qapp, monkeypatch) -> None:
    def make_checks(cancelled=None):
        checks = []
        for index in range(4):
            check = DummyCheck(cancelled=cancelled)
            check.id = f"dummy{index}"  # id должен быть уникальным, как у реальных проверок
            checks.append(check)
        return checks

    monkeypatch.setattr("src.core.engine.all_checks", make_checks)
    engine = DiagnosticEngine()
    loop = QEventLoop()
    captured: list[list[CheckResult]] = []
    engine.finished.connect(lambda results: (captured.append(results), loop.quit()))
    QTimer.singleShot(5000, loop.quit)
    assert engine.start() is True
    loop.exec()
    assert captured, "diagnostics did not finish"
    assert len(captured[0]) == 4
    assert all(item.status == Status.OK for item in captured[0])
    assert engine.is_running is False


def test_fix_engine_dry_run(qapp, monkeypatch) -> None:
    monkeypatch.setattr("src.core.engine.fix_by_id", lambda _id: DummyFix)
    engine = FixEngine()
    loop = QEventLoop()
    captured: list[list[FixResult]] = []
    engine.finished.connect(lambda results: (captured.append(results), loop.quit()))
    QTimer.singleShot(5000, loop.quit)
    assert engine.apply(["dummy_fix", "dummy_fix"], restore_point=False, dry_run=True) is True
    loop.exec()
    assert captured and len(captured[0]) == 2
    assert all(item.success for item in captured[0])
    assert all("dry" in item.details[0] for item in captured[0])
