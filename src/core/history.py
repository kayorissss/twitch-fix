"""История диагностики: JSONL-файл + агрегаты для графика доступности.

Формат строки: {"ts": 1730000000.0, "ok": true, "score": 92, "issues": [...]}
Хранится 7 дней по умолчанию, размер файла ограничен 20 000 записей.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.utils.logger import get_logger
from src.utils.paths import history_path

log = get_logger(__name__)


@dataclass
class Record:
    ts: float
    ok: bool
    score: int = 100
    issues: list[str] = field(default_factory=list)

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.ts, tz=timezone.utc)

    def to_dict(self) -> dict[str, object]:
        return {"ts": self.ts, "ok": self.ok, "score": self.score, "issues": self.issues[:20]}


class History:
    """Потокобезопасное хранилище результатов диагностики/мониторинга."""

    def __init__(self, path: str | Path | None = None, retention_days: int = 7) -> None:
        self.path = Path(path) if path else history_path()
        self.retention_days = max(1, retention_days)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, ok: bool, score: int = 100, issues: Iterable[str] = ()) -> None:
        record = Record(ts=time.time(), ok=ok, score=int(score), issues=list(issues)[:20])
        with self._lock:
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            except OSError as exc:
                log.error("Cannot write history: %s", exc)
                return
            self.prune()

    def add_results(self, results: list) -> None:
        """Добавить запись по итогам полной диагностики."""
        bad = [r for r in results if getattr(r, "status", None) and getattr(r.status, "is_problem", False)]
        score = max(0, 100 - sum(15 if r.status.value == "error" else 6 for r in bad))
        self.add(ok=not bad, score=score, issues=[r.title for r in bad])

    def records(self, since_seconds: float | None = None) -> list[Record]:
        """Прочитать записи начиная с ``since_seconds`` назад (None = все)."""
        if not self.path.exists():
            return []
        threshold = time.time() - since_seconds if since_seconds else 0
        records: list[Record] = []
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        for line in lines[-20_000:]:
            try:
                payload = json.loads(line)
                ts = float(payload.get("ts", 0))
                if ts < threshold:
                    continue
                records.append(
                    Record(
                        ts=ts,
                        ok=bool(payload.get("ok", True)),
                        score=int(payload.get("score", 100)),
                        issues=[str(item) for item in payload.get("issues", [])],
                    )
                )
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
        return records

    def availability(self, hours: int = 24) -> float | None:
        """Процент успешных проверок за период или None, если данных нет."""
        records = self.records(since_seconds=hours * 3600)
        if not records:
            return None
        return round(100.0 * sum(1 for item in records if item.ok) / len(records), 1)

    def buckets(self, hours: int = 24, count: int = 24) -> list[float | None]:
        """Значения для графика: доля успеха в каждом бакете (None = нет данных)."""
        width = hours * 3600 / max(1, count)
        now = time.time()
        buckets: list[list[bool]] = [[] for _ in range(count)]
        for record in self.records(since_seconds=hours * 3600):
            index = int((record.ts - (now - hours * 3600)) / width)
            if 0 <= index < count:
                buckets[index].append(record.ok)
        return [
            round(100.0 * sum(values) / len(values), 1) if values else None for values in buckets
        ]

    def prune(self) -> None:
        """Удалить старые записи и ограничить размер файла."""
        if not self.path.exists():
            return
        cutoff = time.time() - self.retention_days * 86400
        kept: list[str] = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()[-20_000:]
        except OSError:
            return
        for line in lines:
            try:
                if float(json.loads(line).get("ts", 0)) >= cutoff:
                    kept.append(line)
            except (ValueError, json.JSONDecodeError):
                continue
        try:
            self.path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        except OSError as exc:
            log.warning("Cannot prune history: %s", exc)
