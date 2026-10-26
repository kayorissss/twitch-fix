"""Генерация ресурсов TwitchFix: иконки, логотип, баннер и скриншоты UI.

Запуск (из корня проекта):
    QT_QPA_PLATFORM=offscreen python scripts/generate_assets.py

Иконки/баннер рисуются Pillow, скриншоты — реальным Qt-интерфейсом с
демонстрационными результатами диагностики (без сетевых запросов).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Изолируем настройки/логи генератора от данных реального пользователя.
os.environ.setdefault("TWITCHFIX_HOME", str(Path(tempfile.gettempdir()) / "twitchfix-assets"))
ASSETS = ROOT / "assets"
SHOTS = ASSETS / "screenshots"


def make_icon(size: int = 512):
    """Нарисовать иконку: фиолетовый градиент + глитч-пузырь."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    scale = 4
    s = size * scale
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pixels = Image.new("RGBA", (s, s))
    draw = ImageDraw.Draw(pixels)
    for y in range(s):
        t = y / max(1, s - 1)
        for_x = 0.0  # горизонтальный градиент добавляем ниже
        _ = for_x
        r = int(169 + (90 - 169) * t)
        g = int(112 + (31 - 112) * t)
        b = int(255 + (196 - 255) * t)
        draw.line([(0, y), (s, y)], fill=(r, g, b, 255))
    # лёгкий диагональный блик
    highlight = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse((-s * 0.35, -s * 0.55, s * 0.75, s * 0.55), fill=(255, 255, 255, 34))
    pixels = Image.alpha_composite(pixels, highlight)

    mask = Image.new("L", (s, s), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((s * 0.04, s * 0.04, s * 0.96, s * 0.96),
                         radius=int(s * 0.22), fill=255)
    image.paste(pixels, (0, 0), mask)

    d = ImageDraw.Draw(image)
    # Белый чат-пузырь.
    d.rounded_rectangle((s * 0.26, s * 0.22, s * 0.75, s * 0.62),
                        radius=int(s * 0.07), fill=(255, 255, 255, 255))
    d.polygon([
        (s * 0.40, s * 0.58), (s * 0.40, s * 0.78), (s * 0.57, s * 0.60),
    ], fill=(255, 255, 255, 255))
    # Глитч-полоски цветом фона.
    d.rounded_rectangle((s * 0.37, s * 0.32, s * 0.43, s * 0.52),
                        radius=int(s * 0.012), fill=(145, 70, 255, 255))
    d.rounded_rectangle((s * 0.55, s * 0.32, s * 0.61, s * 0.52),
                        radius=int(s * 0.012), fill=(145, 70, 255, 255))
    return image.resize((size, size), Image.LANCZOS)


def write_icons() -> None:
    from PIL import Image  # noqa: PLC0415

    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = make_icon(512)
    icon.save(ASSETS / "icon.png")
    icon.save(
        ASSETS / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    Image.new("RGBA", (1, 1), (0, 0, 0, 0))  # держим Pillow импортированным
    print("icons: icon.png, icon.ico")


LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#a970ff"/>
      <stop offset="0.5" stop-color="#9146ff"/>
      <stop offset="1" stop-color="#5a1fc4"/>
    </linearGradient>
  </defs>
  <rect x="4" y="4" width="120" height="120" rx="28" fill="url(#g)"/>
  <path d="M36 30 H94 V77 H72 L54 97 V77 H36 Z" fill="#fff"/>
  <rect x="50" y="42" width="8" height="23" rx="3" fill="#9146ff"/>
  <rect x="72" y="42" width="8" height="23" rx="3" fill="#9146ff"/>
</svg>
"""

BANNER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 320" width="1200" height="320">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1a1a2e"/>
      <stop offset="0.55" stop-color="#221a44"/>
      <stop offset="1" stop-color="#12121f"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#a970ff"/>
      <stop offset="1" stop-color="#00d4ff"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="320" rx="24" fill="url(#bg)"/>
  <circle cx="1050" cy="60" r="180" fill="#9146ff" opacity="0.10"/>
  <circle cx="140" cy="300" r="160" fill="#00d4ff" opacity="0.07"/>
  <g transform="translate(64,66) scale(1.35)">
    <rect x="4" y="4" width="120" height="120" rx="28" fill="url(#accent)"/>
    <path d="M36 30 H94 V77 H72 L54 97 V77 H36 Z" fill="#fff"/>
    <rect x="50" y="42" width="8" height="23" rx="3" fill="#9146ff"/>
    <rect x="72" y="42" width="8" height="23" rx="3" fill="#9146ff"/>
  </g>
  <text x="290" y="145" fill="#ffffff" font-family="Segoe UI, Arial, sans-serif" font-size="74" font-weight="700">TwitchFix</text>
  <text x="294" y="196" fill="#b9c4e8" font-family="Segoe UI, Arial, sans-serif" font-size="26">Diagnose &amp; repair your Twitch connection — in one click.</text>
  <text x="294" y="238" fill="#9146ff" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="600">13 checks  •  9 auto-fixes  •  Windows 10/11</text>
</svg>
"""


def write_vectors() -> None:
    (ASSETS / "logo.svg").write_text(LOGO_SVG, encoding="utf-8")
    (ASSETS / "banner.svg").write_text(BANNER_SVG, encoding="utf-8")
    print("vectors: logo.svg, banner.svg")


def make_banner_png() -> None:
    """Растровый баннер для мест, где SVG не отображается."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    w, h = 1200, 320
    image = Image.new("RGB", (w, h), (26, 26, 46))
    draw = ImageDraw.Draw(image)
    for x in range(w):
        t = x / w
        draw.line([(x, 0), (x, h)], fill=(
            int(26 + 18 * t), int(26 + 10 * t), int(46 + 28 * t)
        ))
    icon = make_icon(256)
    image.paste(icon, (64, 42), icon)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    def font(paths, size):
        for path in paths:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    draw.text((350, 92), "TwitchFix", font=font(font_paths, 68), fill=(255, 255, 255))
    draw.text((354, 180), "Diagnose & repair your Twitch connection — in one click.",
              font=font(regular_paths, 24), fill=(185, 196, 232))
    draw.text((354, 222), "13 checks  •  9 auto-fixes  •  Windows 10/11",
              font=font(font_paths, 20), fill=(169, 112, 255))
    image.save(ASSETS / "banner.png")
    print("banner: banner.png")


def demo_results():
    """Демонстрационные результаты для скриншотов (без сети)."""
    from src.core.diagnostics import CHECK_CLASSES  # noqa: PLC0415
    from src.core.diagnostics.base_check import CheckResult, Status  # noqa: PLC0415

    presets = {
        "hosts": (Status.ERROR, "Найдено 3 twitch-записей в hosts", "Found 3 Twitch-related hosts entries", ["L24: 0.0.0.0 twitch.tv  [zapret]", "L25: 0.0.0.0 gql.twitch.tv  [zapret]", "L26: 0.0.0.0 usher.ttvnw.net  [zapret]"], {"antivirus": ""}),
        "dns": (Status.WARNING, "DNS работает, но отвечает медленно", "DNS works but responds slowly", ["www.twitch.tv: 151.101.66.167 (412 ms)", "gql.twitch.tv: 151.101.194.167 (389 ms)", "average system lookup: 394 ms"]),
        "tcp": (Status.OK, "TCP 443/80 доступны, средняя задержка 38 ms", "TCP 443/80 reachable, average latency 38 ms", ["OK www.twitch.tv:443 151.101.66.167 36 ms", "OK gql.twitch.tv:443 151.101.194.167 41 ms"]),
        "ssl": (Status.ERROR, "Сертификат подменён: Kaspersky (HTTPS-сканирование)", "Certificate replaced by Kaspersky (HTTPS scanning)", ["issuer: Kaspersky Lab", "valid: Aug  1 00:00:00 2026 GMT -> Aug  1 00:00:00 2027 GMT", "MITM vendor: Kaspersky"], {"antivirus": "Kaspersky"}),
        "http": (Status.WARNING, "Проблемы с HTTP: GraphQL HTTP 403", "HTTP problems: GraphQL HTTP 403", ["GET https://www.twitch.tv -> 200 (418233 bytes)", "POST https://gql.twitch.tv/gql -> 403 (142 bytes)"]),
        "twitch_api": (Status.WARNING, "Не работает: chat", "Not working: chat", ["site: OK — HTTP 200", "api: OK — HTTP 200", "video: OK — HTTP 200", "chat: FAIL — SSL: sslv3 alert handshake failure"]),
        "time": (Status.OK, "Время синхронизировано (отклонение +0.4 с)", "Time is synchronized (offset +0.4 s)", ["local: 2026-10-26T17:45:00+00:00", "offset (server - local): +0.4 s"]),
        "proxy": (Status.WARNING, "Обнаружен активный прокси (env:HTTPS_PROXY)", "Active proxy detected (env:HTTPS_PROXY)", ["env HTTPS_PROXY = http://127.0.0.1:8888", "WinHTTP proxy: direct access"]),
        "firewall": (Status.OK, "Блокирующих правил для Twitch нет", "No blocking rules for Twitch", ["firewall profiles: enabled", "relevant outbound block rules: 0"]),
        "network": (Status.OK, "Адаптер настроен корректно (wi-fi, MTU 1500)", "Adapter looks fine (wi-fi, MTU 1500)", ["local IP: 192.168.1.37", "gateway: 192.168.1.1", "DNS servers: 192.168.1.1, 8.8.8.8"]),
        "process": (Status.WARNING, "Найдено конфликтующих комбинаций: 2", "Conflicting combinations found: 2", ["DPI-обход: goodbyedpi.exe", "VPN-клиенты: wireguard.exe", "CONFLICT: DPI bypass + VPN"]),
        "ping": (Status.OK, "Маршрут до Twitch стабилен", "Route to Twitch is stable", ["ping www.twitch.tv: OK avg=34.2 ms loss=0%", "1. 192.168.1.1  2 ms", "2. 10.0.0.1  9 ms"]),
        "browser": (Status.OK, "Браузер и кэш в порядке", "Browser and cache look healthy", ["installed browsers: Google Chrome, Microsoft Edge", "Google Chrome [Default]: extensions=7, cache=214.5 MB"]),
    }
    order = ["hosts", "dns", "tcp", "ssl", "http", "twitch_api", "time", "proxy",
             "firewall", "network", "process", "ping", "browser"]
    by_id = {cls.id: cls for cls in CHECK_CLASSES}
    results = []
    for index, check_id in enumerate(order):
        cls = by_id[check_id]
        status, ru, en, details, *rest = presets[check_id]
        results.append(
            CheckResult(
                id=check_id,
                title=cls.title_ru,
                title_en=cls.title_en,
                status=status,
                summary=ru,
                summary_en=en,
                details=details,
                data=rest[0] if rest else {},
                fix_id=cls.fix_id if status.is_problem else None,
                duration_ms=120 + index * 37,
            )
        )
    return results


def make_screenshots() -> None:
    import json  # noqa: PLC0415
    import tempfile  # noqa: PLC0415
    import time  # noqa: PLC0415

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.app import TwitchFixApplication  # noqa: PLC0415
    from src.config.i18n import i18n  # noqa: PLC0415
    from src.core.history import History  # noqa: PLC0415
    from src.core.report_generator import ReportGenerator  # noqa: PLC0415
    from src.ui import theme as theme_module  # noqa: PLC0415
    from src.utils.system_info import SystemInfo  # noqa: PLC0415

    SHOTS.mkdir(parents=True, exist_ok=True)
    app = TwitchFixApplication(["twitchfix", "--demo"])
    window = app.window
    window.monitor.stop()  # не дёргаем сеть во время съёмки
    window.diagnostics.btn_stop.setEnabled(False)
    i18n.set_language("ru")
    theme_module.load_theme("dark")
    window._refresh_icons()

    # Демонстрационная история за 24 часа (для графика доступности).
    demo_path = Path(tempfile.gettempdir()) / "twitchfix_demo_history.jsonl"
    now = time.time()
    records = []
    for index in range(48):
        ok = index not in (7, 8, 29, 30)
        records.append({
            "ts": now - (48 - index) * 1800,
            "ok": ok,
            "score": 100 if ok else 55,
            "issues": [] if ok else ["dns"],
        })
    demo_path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
    demo_history = History(path=demo_path, retention_days=7)
    window.history = demo_history
    window.dashboard.history = demo_history
    window.report.history = demo_history
    window.monitor.history = demo_history
    results = demo_results()
    window.set_demo_results(results)
    fake_system = SystemInfo(
        os="Windows", release="10.0.22631 (Windows 11 Pro)", architecture="AMD64",
        python="3.11.9", admin=True, local_ip="192.168.1.37", gateway="192.168.1.1",
        dns_servers=["192.168.1.1", "8.8.8.8"], mtu=1500, connection_type="wi-fi",
        ipv6_available=True, browsers=["Google Chrome", "Microsoft Edge"],
    )
    generator = ReportGenerator(results=results, system=fake_system,
                                history=demo_history, language="ru")
    window.report.set_report(generator)
    window.resize(1280, 800)
    window.show()
    app.processEvents()

    pages = [
        (0, "dashboard.png"),
        (1, "diagnostics.png"),
        (2, "autofix.png"),
        (3, "report.png"),
        (4, "settings.png"),
    ]
    def settle(delay: float = 0.35) -> None:
        """Дождаться завершения анимаций и полной перерисовки окна."""
        time.sleep(delay)
        app.processEvents()
        window.repaint()
        app.processEvents()

    for index, name in pages:
        window.stack.setCurrentIndex(index)
        window.sidebar.set_active(index)
        app.processEvents()
        settle()
        window.grab().save(str(SHOTS / name))
        print("screenshot:", name)

    # Светлая тема и компактное окно.
    theme_module.load_theme("light")
    window._refresh_icons()
    window.retranslate_all()
    window.stack.setCurrentIndex(0)
    window.sidebar.set_active(0)
    app.processEvents()
    settle()
    window.grab().save(str(SHOTS / "light_theme.png"))
    print("screenshot: light_theme.png")

    theme_module.load_theme("dark")
    window._refresh_icons()
    window.retranslate_all()
    window.set_compact(True)
    for toast in list(window.toasts.toasts):
        toast.hide()
    window.toasts.toasts.clear()
    window.stack.setCurrentIndex(0)
    app.processEvents()
    settle(0.6)
    window.grab().save(str(SHOTS / "compact.png"))
    print("screenshot: compact.png")
    window.monitor.stop()
    app.quit()


def make_demo_gif() -> None:
    from PIL import Image  # noqa: PLC0415

    names = ["dashboard.png", "diagnostics.png", "autofix.png", "report.png"]
    frames = []
    for name in names:
        path = SHOTS / name
        if path.exists():
            image = Image.open(path).convert("RGB")
            image.thumbnail((960, 600))
            frames.append(image)
    if frames:
        frames[0].save(
            ASSETS / "demo.gif", save_all=True, append_images=frames[1:],
            duration=1400, loop=0, optimize=True,
        )
        print("demo: demo.gif")


if __name__ == "__main__":
    write_icons()
    write_vectors()
    make_banner_png()
    make_screenshots()
    make_demo_gif()
