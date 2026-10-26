"""Фоновый мониторинг доступности Twitch (каждые N минут, без блокировки UI).

Быстрая проверка: GET twitch.tv + POST gql.twitch.tv в worker-потоке. При
смене состояния испускается сигнал state_changed(ok, message), который UI
использует для уведомлений в системном трее.
"""
from __future__ import annotations

from typing import Any

import requests
from PyQt6.QtCore import QObject, Qt, QThreadPool, QRunnable, QTimer, pyqtSignal

from src.config.constants import GQL_QUERY, GQL_URL, TWITCH_WEB_CLIENT_ID, USER_AGENT
from src.config.i18n import i18n
from src.core.history import History
from src.utils.logger import get_logger

log = get_logger(__name__)


class _MonitorSignals(QObject):
    checked = pyqtSignal(bool, str)


class _Probe(QRunnable):
    def __init__(self, signals: _MonitorSignals, history: History) -> None:
        super().__init__()
        self.signals = signals
        self.history = history

    def run(self) -> None:
        ok = False
        issues: list[str] = []
        try:
            site = requests.get(
                "https://www.twitch.tv", headers={"User-Agent": USER_AGENT}, timeout=5.0
            )
            ok = site.status_code < 400
            if not ok:
                issues.append(f"site HTTP {site.status_code}")
        except requests.RequestException as exc:
            issues.append(f"site: {type(exc).__name__}")
        try:
            gql = requests.post(
                GQL_URL,
                headers={"Client-ID": TWITCH_WEB_CLIENT_ID, "Content-Type": "application/json"},
                json={"query": GQL_QUERY},
                timeout=5.0,
            )
            if gql.status_code >= 500:
                ok = False
                issues.append(f"gql HTTP {gql.status_code}")
            elif gql.status_code in (401, 403):
                issues.append("gql client-id rejected")
        except requests.RequestException as exc:
            ok = False
            issues.append(f"gql: {type(exc).__name__}")

        message = i18n.tr("monitor.check_ok") if ok else i18n.tr("monitor.check_fail")
        self.history.add(ok=ok, score=100 if ok else 40, issues=issues)
        self.signals.checked.emit(ok, message)
        log.info("Monitor probe: ok=%s issues=%s", ok, issues)


class Monitor(QObject):
    """Периодическая проверка с уведомлением о потере/восстановлении связи."""

    state_changed = pyqtSignal(bool, str)
    checked = pyqtSignal(bool, str)
    log = pyqtSignal(str, str)

    def __init__(self, settings: Any, history: History | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.history = history or History(retention_days=int(settings.get("history_days")))
        self.signals = _MonitorSignals()
        self.signals.checked.connect(self._on_checked)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.check_now)
        self._last_state: bool | None = None
        self._probing = False

    def start(self) -> None:
        interval = max(1, int(self.settings.get("monitor_interval"))) * 60_000
        self.timer.start(interval)
        # Первую проверку делаем через 45 секунд, чтобы не нагружать запуск.
        QTimer.singleShot(45_000, self.check_now)
        log.info("Monitor started, interval=%d min", interval // 60_000)

    def stop(self) -> None:
        self.timer.stop()
        log.info("Monitor stopped")

    def apply_settings(self) -> None:
        if self.settings.get("monitoring"):
            self.start()
        else:
            self.stop()

    def check_now(self) -> None:
        if self._probing:
            return
        self._probing = True
        self.pool.start(_Probe(self.signals, self.history))

    def _on_checked(self, ok: bool, message: str) -> None:
        self._probing = False
        self.checked.emit(ok, message)
        self.log.emit("ok" if ok else "err", f"Monitor: {message}")
        if self._last_state is None:
            self._last_state = ok
            return
        if self._last_state != ok:
            self._last_state = ok
            self.state_changed.emit(ok, message)
            log.info("Monitor state changed -> %s", "online" if ok else "offline")
