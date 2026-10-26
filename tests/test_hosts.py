"""Тесты парсера hosts и авто-исправления (на временном файле, без UAC)."""
from __future__ import annotations

from pathlib import Path

from src.core.diagnostics.hosts_check import parse_hosts
from src.core.fixes.hosts_fix import HostsFix, clean_hosts
from src.utils.backup import BackupManager

SAMPLE = """# localhost
127.0.0.1 localhost
# zapret start  <- источник блокировок
0.0.0.0 twitch.tv
0.0.0.0 gql.twitch.tv # API
0.0.0.0 usher.ttvnw.net
192.168.1.10 my-nas.local
# keep me
"""


def test_parse_finds_all_twitch_entries(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    path.write_text(SAMPLE, encoding="utf-8")
    entries = parse_hosts(path)
    assert len(entries) == 3
    assert [entry.line_no for entry in entries] == [4, 5, 6]
    assert {entry.keyword for entry in entries} >= {"twitch", "ttvnw"}
    assert all(entry.tool == "zapret" for entry in entries)


def test_parse_ignores_comments_and_unrelated_lines(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    path.write_text("# twitch.tv mentioned in a comment only\n10.0.0.1 nas\n", encoding="utf-8")
    assert parse_hosts(path) == []


def test_clean_hosts_removes_only_twitch_lines_with_backup(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    path.write_text(SAMPLE, encoding="utf-8")
    backup = BackupManager(session="unit-test")
    removed, backup_path, error = clean_hosts(path, backup=backup)
    assert error == ""
    assert removed == 3
    assert backup_path is not None and backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == SAMPLE
    remaining = path.read_text(encoding="utf-8")
    assert "my-nas.local" in remaining
    assert "# keep me" in remaining
    assert "twitch" not in remaining
    # Повторная очистка ничего не меняет.
    assert clean_hosts(path, backup=backup)[0] == 0


def test_clean_hosts_dry_run_does_not_touch_file(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    path.write_text(SAMPLE, encoding="utf-8")
    before = path.read_bytes()
    removed, backup_path, error = clean_hosts(path, dry_run=True)
    assert removed == 3 and backup_path is None and error == ""
    assert path.read_bytes() == before


def test_hosts_check_and_fix_on_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    path.write_text(SAMPLE, encoding="utf-8")
    # Явно тестируем fix с переопределённым путём.
    fix = HostsFix(backup=BackupManager(session="unit-test-2"), path=path)
    result = fix.apply(dry_run=False)
    assert result.success
    assert path.read_text(encoding="utf-8").count("twitch") == 0
