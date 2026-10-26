"""Проверка №6: системное время.

Запрашивает NTP (pool.ntp.org, UDP/123) без внешних библиотек и сравнивает с
локальными часами. Расхождение > 5 минут ломает TLS и авторизацию Twitch.
"""
from __future__ import annotations

import socket
import struct
import time
from datetime import datetime, timezone

from src.config.constants import MAX_TIME_SKEW_SECONDS, NTP_PORT, NTP_SERVER
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status

NTP_DELTA = 2208988800  # секунд между 1900-01-01 и 1970-01-01


def ntp_offset(server: str = NTP_SERVER, timeout: float = 3.0) -> float | None:
    """Вернуть разницу (NTP time - local time) в секундах или None."""
    packet = bytearray(48)
    packet[0] = 0b00011011  # LI=0, VN=3, Mode=3 (client)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sent = time.time()
            sock.sendto(bytes(packet), (server, NTP_PORT))
            data, _ = sock.recvfrom(48)
            received = time.time()
    except OSError:
        return None
    if len(data) < 48:
        return None
    unpacked = struct.unpack("!12I", data[:48])
    server_time = unpacked[10] + float(unpacked[11]) / 2**32 - NTP_DELTA
    local_midpoint = (sent + received) / 2
    return server_time - local_midpoint


class TimeCheck(BaseCheck):
    id = "time"
    title_ru = "Системное время"
    title_en = "System time"
    icon = "clock"
    fix_id = "time"
    timeout = 10.0

    def run(self) -> CheckResult:
        offset = ntp_offset()
        now = datetime.now(timezone.utc).astimezone()
        details = [
            f"local: {now.isoformat(timespec='seconds')}",
            f"NTP server: {NTP_SERVER}",
            f"allowed skew: +/-{MAX_TIME_SKEW_SECONDS} s",
        ]
        data: dict[str, object] = {"local": now.isoformat(timespec="seconds")}
        if offset is None:
            details.append("NTP unavailable (UDP/123 blocked or no network)")
            return self.result(
                Status.WARNING,
                "Не удалось сверить время с NTP-сервером",
                "Could not verify time with NTP server",
                details=details,
                data=data,
                fix_id=None,
            )
        details.append(f"offset (server - local): {offset:+.1f} s")
        data["offset_seconds"] = round(offset, 2)
        if abs(offset) > MAX_TIME_SKEW_SECONDS:
            return self.result(
                Status.ERROR,
                f"Часы спешат/отстают на {abs(offset) / 60:.1f} мин — это ломает TLS",
                f"Clock is off by {abs(offset) / 60:.1f} min — this breaks TLS",
                details=details,
                data=data,
            )
        return self.result(
            Status.OK,
            f"Время синхронизировано (отклонение {offset:+.1f} с)",
            f"Time is synchronized (offset {offset:+.1f} s)",
            details=details,
            data=data,
            fix_id=None,
        )
