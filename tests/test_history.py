"""История: запись, агрегаты, бакеты, очистка старых данных."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.core.history import History


def test_add_and_availability(tmp_path: Path) -> None:
    history = History(path=tmp_path / "history.jsonl")
    assert history.availability(24) is None
    history.add(True, 100)
    history.add(True, 100)
    history.add(False, 40, issues=["dns"])
    assert history.availability(24) == pytest.approx(66.7, abs=0.1)
    assert len(history.records()) == 3


def test_buckets_count_and_none_for_empty(tmp_path: Path) -> None:
    history = History(path=tmp_path / "history.jsonl")
    history.add(True, 100)
    buckets = history.buckets(24, 12)
    assert len(buckets) == 12
    assert sum(1 for value in buckets if value is not None) >= 1


def test_prune_removes_old_records(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    old = time.time() - 30 * 86400
    path.write_text(
        json.dumps({"ts": old, "ok": True, "score": 100, "issues": []}) + "\n"
        + json.dumps({"ts": time.time(), "ok": True, "score": 100, "issues": []}) + "\n",
        encoding="utf-8",
    )
    history = History(path=path, retention_days=7)
    history.prune()
    assert len(history.records()) == 1
