"""Общие фикстуры pytest: изолируем пользовательские данные приложения."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TWITCHFIX_HOME", str(tmp_path / "appdata"))
    yield tmp_path / "appdata"
