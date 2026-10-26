"""Сведения о системе и безопасный запуск консольных команд Windows.

Все команды имеют таймаут и скрытое окно консоли, а результат всегда
возвращается как текст: UI не должен падать, если утилита отсутствует.
"""
from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Sequence

from src.config.constants import BROWSER_PATHS
from src.utils.logger import get_logger

log = get_logger(__name__)


def _no_window() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "cp866" if sys.platform == "win32" else "utf-8", "cp1251", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def run_command(
    args: Sequence[str], timeout: float = 10.0, shell: bool = False
) -> tuple[int, str, str]:
    """Запустить команду и вернуть (код, stdout, stderr). Исключений не бросает."""
    try:
        proc = subprocess.run(
            list(args) if not shell else args,
            capture_output=True,
            timeout=timeout,
            shell=shell,
            creationflags=_no_window(),
            check=False,
        )
        return proc.returncode, _decode(proc.stdout or b""), _decode(proc.stderr or b"")
    except FileNotFoundError:
        return 127, "", "command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except OSError as exc:
        return 1, "", str(exc)


@dataclass
class SystemInfo:
    """Данные для отчёта (без паролей, токенов и имён пользователей)."""

    os: str = ""
    release: str = ""
    architecture: str = ""
    python: str = ""
    admin: bool = False
    hostname: str = ""
    local_ip: str = ""
    gateway: str = ""
    dns_servers: list[str] = field(default_factory=list)
    mtu: int | None = None
    connection_type: str = "unknown"
    ipv6_available: bool = False
    browsers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return ""


def _default_gateway() -> str:
    if sys.platform == "win32":
        _, out, _ = run_command(["route", "print", "0.0.0.0"], timeout=6)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "0.0.0.0":
                return parts[2]
    else:
        _, out, _ = run_command(["ip", "route"], timeout=4)
        for line in out.splitlines():
            if line.startswith("default via "):
                return line.split()[2]
    return ""


def _dns_servers() -> list[str]:
    servers: list[str] = []
    if sys.platform == "win32":
        _, out, _ = run_command(["netsh", "interface", "ipv4", "show", "dnsservers"], timeout=8)
        for line in out.splitlines():
            token = line.strip().split()
            if token and (token[0].count(".") == 3 or ":" in token[0]):
                if token[0] not in servers:
                    servers.append(token[0])
    else:
        try:
            for line in open("/etc/resolv.conf", encoding="utf-8", errors="replace"):
                if line.startswith("nameserver"):
                    servers.append(line.split()[1])
        except OSError:
            pass
    return servers


def _mtu() -> int | None:
    if sys.platform == "win32":
        _, out, _ = run_command(["netsh", "interface", "ipv4", "show", "subinterfaces"], timeout=8)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit() and int(parts[0]) > 500:
                return int(parts[0])
    else:
        _, out, _ = run_command(["ip", "link"], timeout=4)
        for line in out.splitlines():
            if "mtu" in line and "state UP" in line:
                try:
                    return int(line.split("mtu")[1].split()[0])
                except (ValueError, IndexError):
                    continue
    return None


def _connection_type(gateway: str) -> str:
    """Эвристика по шлюзу/имени адаптера: мобильная раздача, Wi-Fi, Ethernet."""
    import psutil  # noqa: PLC0415 - импорт здесь дешевле при частых вызовах

    names = " ".join(psutil.net_if_stats().keys()).lower()
    if any(word in names for word in ("mobile", "wwan", "cellular", "usb tether", "раздача")):
        return "mobile"
    if any(word in names for word in ("wi-fi", "wifi", "wireless", "wlan", "беспровод")):
        return "wi-fi"
    if gateway.startswith("192.168.43.") or gateway.startswith("192.168.137."):
        return "mobile"
    return "ethernet" if gateway else "unknown"


def installed_browsers() -> list[str]:
    """Найти установленные браузеры по стандартным путям и в PATH."""
    found: list[str] = []
    for name, paths in BROWSER_PATHS.items():
        if any(os.path.isfile(path) for path in paths):
            found.append(name)
            continue
        executable = paths[0].rsplit("\\", 1)[-1]
        if shutil.which(executable) or shutil.which(executable.replace(".exe", "")):
            found.append(name)
    return found


def quick_system_info(admin: bool = False) -> SystemInfo:
    """Быстрый снимок системы БЕЗ запуска консольных команд.

    Используется при генерации отчёта из UI-потока: сетевые детали (IP,
    шлюз, DNS, MTU) уже содержатся в результатах проверки «Сетевой адаптер»,
    поэтому здесь достаточно данных Python stdlib.
    """
    info = SystemInfo(
        os=platform.system(),
        release=platform.release(),
        architecture=platform.machine(),
        python=platform.python_version(),
        admin=admin,
        ipv6_available=socket.has_ipv6,
        connection_type="unknown",
    )
    try:
        info.browsers = installed_browsers()
    except Exception:
        pass
    return info


def gather(admin: bool = False) -> SystemInfo:
    """Полная информация о системе (запускает netsh/ip/route; вызывать не из UI)."""
    info = SystemInfo(
        os=platform.system(),
        release=f"{platform.release()} ({platform.version()})"[:120],
        architecture=platform.machine(),
        python=platform.python_version(),
        admin=admin,
        hostname=socket.gethostname(),
        local_ip=_local_ip(),
        gateway=_default_gateway(),
        dns_servers=_dns_servers(),
        mtu=_mtu(),
        ipv6_available=socket.has_ipv6,
    )
    try:
        info.connection_type = _connection_type(info.gateway)
    except Exception as exc:
        log.warning("Connection type detection failed: %s", exc)
    try:
        info.browsers = installed_browsers()
    except Exception as exc:
        log.warning("Browser detection failed: %s", exc)
    return info
