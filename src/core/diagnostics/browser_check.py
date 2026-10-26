"""Проверка №12: браузеры, расширения и кэш.

Ищет установленные браузеры, считает расширения и объём кэша профилей.
Повреждённый/раздутый кэш — частая причина «бесконечной загрузки» Twitch.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.utils.system_info import installed_browsers

CACHE_LIMIT_MB = 700
EXTENSION_LIMIT = 60


def _home() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home())


def profile_dirs() -> dict[str, list[Path]]:
    """Вернуть известные каталоги пользовательских данных браузеров."""
    if sys.platform == "win32":
        base = _home()
        candidates = {
            "Google Chrome": [base / "Google" / "Chrome" / "User Data"],
            "Microsoft Edge": [base / "Microsoft" / "Edge" / "User Data"],
            "Brave": [base / "BraveSoftware" / "Brave-Browser" / "User Data"],
            "Opera": [base / "Opera Software" / "Opera Stable"],
            "Mozilla Firefox": [base.parent / "Roaming" / "Mozilla" / "Firefox" / "Profiles"],
        }
    else:
        base = Path.home()
        candidates = {
            "Google Chrome": [base / ".config" / "google-chrome"],
            "Mozilla Firefox": [base / ".mozilla" / "firefox"],
            "Brave": [base / ".config" / "BraveSoftware" / "Brave-Browser"],
        }
    return {name: [p for p in paths if p.exists()] for name, paths in candidates.items()}


def count_extensions(profile: Path) -> int:
    """Количество установленных расширений (по каталогам Extensions)."""
    total = 0
    for extension_dir in profile.rglob("Extensions"):
        try:
            total += sum(1 for item in extension_dir.iterdir() if item.is_dir())
        except OSError:
            continue
        if total > 500:
            break
    return total


def cache_size_mb(profile: Path) -> float:
    """Размер кэша профиля в МБ (ограничиваем обход 20 000 файлами)."""
    size = 0
    scanned = 0
    for cache_dir in profile.rglob("*"):
        if not cache_dir.is_dir() or cache_dir.name.lower() not in (
            "cache", "cache_data", "code cache", "gpuCache", "cache2"
        ):
            continue
        try:
            for file in cache_dir.rglob("*"):
                if scanned >= 20_000:
                    break
                if file.is_file():
                    size += file.stat().st_size
                    scanned += 1
        except (OSError, PermissionError):
            continue
    return round(size / (1024 * 1024), 1)


class BrowserCheck(BaseCheck):
    id = "browser"
    title_ru = "Браузер и кэш"
    title_en = "Browser and cache"
    icon = "browser"
    fix_id = "cache"
    timeout = 25.0

    def run(self) -> CheckResult:
        browsers = installed_browsers()
        directories = profile_dirs()
        details = [f"installed browsers: {', '.join(browsers) if browsers else 'none detected'}"]
        problems: list[str] = []
        data_browsers: list[dict[str, object]] = []

        for name, paths in directories.items():
            if not paths:
                continue
            for profile in paths[:4]:
                extensions = count_extensions(profile)
                cache_mb = cache_size_mb(profile)
                details.append(
                    f"{name} [{profile.name}]: extensions={extensions}, cache={cache_mb} MB"
                )
                data_browsers.append(
                    {"name": name, "profile": str(profile), "extensions": extensions, "cache_mb": cache_mb}
                )
                if cache_mb > CACHE_LIMIT_MB:
                    problems.append(f"{name}: cache {cache_mb} MB > {CACHE_LIMIT_MB} MB")
                if extensions > EXTENSION_LIMIT:
                    problems.append(f"{name}: {extensions} extensions (too many)")

        if not browsers and not data_browsers:
            details.append("No browser profiles found in standard locations")
        data = {"browsers": data_browsers, "installed": browsers, "problems": problems}
        if problems:
            return self.result(
                Status.WARNING,
                f"Браузер требует внимания ({len(problems)} проблем)",
                f"Browser needs attention ({len(problems)} issues)",
                details=details + ["issues: " + "; ".join(problems)],
                data=data,
            )
        return self.result(
            Status.OK,
            "Браузер и кэш в порядке",
            "Browser and cache look healthy",
            details=details,
            data=data,
            fix_id=None,
        )
