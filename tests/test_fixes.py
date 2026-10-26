"""Реестр исправлений, dry-run и проверка прав/платформы."""
from __future__ import annotations

from pathlib import Path

from src.core.diagnostics.base_check import CheckResult, Status
from src.core.fixes import all_fixes, fix_by_id, fixes_for_results
from src.core.fixes.cache_fix import CacheFix
from src.core.fixes.dns_fix import DNSFix
from src.core.fixes.hosts_fix import HostsFix
from src.utils.backup import BackupManager


def test_registry_unique_ids() -> None:
    fixes = all_fixes()
    assert len(fixes) >= 9
    assert len({fix.id for fix in fixes}) == len(fixes)
    assert fix_by_id("hosts") is HostsFix
    assert fix_by_id("does-not-exist") is None


def test_fixes_for_results_deduplicates() -> None:
    results = [
        CheckResult("http", "HTTP", "HTTP", Status.WARNING, "warn", "warn", fix_id="proxy"),
        CheckResult("twitch_api", "API", "API", Status.ERROR, "err", "err", fix_id="proxy"),
        CheckResult("dns", "DNS", "DNS", Status.OK, "ok", "ok"),
    ]
    fixes = fixes_for_results(results)
    assert [fix.id for fix in fixes] == ["proxy"]


def test_dry_run_never_changes_files(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    path.write_text("0.0.0.0 twitch.tv\n127.0.0.1 localhost\n", encoding="utf-8")
    before = path.read_bytes()
    fix = HostsFix(backup=BackupManager(session="dry"), path=path)
    result = fix.apply(dry_run=True)
    assert result.success
    assert path.read_bytes() == before


def test_windows_only_fix_reports_unavailable_on_posix() -> None:
    import sys  # noqa: PLC0415

    if sys.platform == "win32":
        return
    fix = DNSFix()
    assert fix.can_apply()[0] is False
    result = fix.safe_apply()
    assert result.success is False
    assert "Windows" in result.message


def test_cache_fix_dry_run() -> None:
    result = CacheFix().apply(dry_run=True)
    assert result.success
    assert isinstance(result.details, list)
