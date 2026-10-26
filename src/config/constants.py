"""Глобальные константы TwitchFix: домены, порты, цвета, сигнатуры ПО.

Файл не содержит исполняемого сетевого кода — только данные. Все проверки и
исправления берут списки доменов/процессов отсюда, чтобы их можно было легко
дополнять и покрывать тестами.
"""
from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "TwitchFix"
APP_VERSION = "1.0.0"
APP_ORG = "TwitchFix"
GITHUB_URL = "https://github.com/kayorissss/twitch-fix"
REPORT_ISSUE_URL = f"{GITHUB_URL}/issues"
DEFAULT_LANGUAGE = "ru"

# ---------------------------------------------------------------- сети Twitch
TWITCH_DOMAINS: tuple[str, ...] = (
    "twitch.tv",
    "www.twitch.tv",
    "gql.twitch.tv",
    "api.twitch.tv",
    "passport.twitch.tv",
    "pubsub-edge.twitch.tv",
    "irc-ws.chat.twitch.tv",
    "usher.ttvnw.net",
    "static.ttvnw.net",
    "video-edge.twitch.tv",
)

# video-weaver.*.hls.ttvnw.net — динамические CDN-хосты конкретных регионов.
# Используются как representative samples: отказ всех из них = проблемы с видео.
VIDEO_WEAVER_DOMAINS: tuple[str, ...] = (
    "video-weaver.fra02.hls.ttvnw.net",
    "video-weaver.ams02.hls.ttvnw.net",
    "video-weaver.lhr01.hls.ttvnw.net",
    "video-weaver.prg01.hls.ttvnw.net",
    "video-weaver.sto02.hls.ttvnw.net",
)

DNS_DOMAINS: tuple[str, ...] = TWITCH_DOMAINS + VIDEO_WEAVER_DOMAINS
DNS_KEY_DOMAINS: tuple[str, ...] = (
    "www.twitch.tv",
    "gql.twitch.tv",
    "usher.ttvnw.net",
    "static.ttvnw.net",
    "irc-ws.chat.twitch.tv",
)
TCP_DOMAINS: tuple[str, ...] = (
    "www.twitch.tv",
    "gql.twitch.tv",
    "usher.ttvnw.net",
    "static.ttvnw.net",
    "irc-ws.chat.twitch.tv",
)
TCP_PORTS: tuple[int, ...] = (443, 80)
PING_HOSTS: tuple[str, ...] = ("www.twitch.tv", "usher.ttvnw.net", "static.ttvnw.net")
TRACEROUTE_HOST = "www.twitch.tv"

# Публичный Client-ID веб-клиента Twitch (используется браузером на twitch.tv).
# Нужен для диагностического GraphQL-запроса; не является секретом.
TWITCH_WEB_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
GQL_URL = "https://gql.twitch.tv/gql"
GQL_QUERY = "query { user(login: \"twitch\") { id login } }"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

GOOGLE_DNS = ("8.8.8.8", "8.8.4.4")
CLOUDFLARE_DNS = ("1.1.1.1", "1.0.0.1")
PREFERRED_DNS = CLOUDFLARE_DNS + GOOGLE_DNS[:1]
PUBLIC_DNS_FALLBACK = "8.8.8.8"
NTP_SERVER = "pool.ntp.org"
NTP_PORT = 123
MAX_TIME_SKEW_SECONDS = 300

# ------------------------------------------------------------------- hosts
HOSTS_KEYWORDS: tuple[str, ...] = (
    "twitch",
    "ttvnw",
    "usher",
    "video-weaver",
    "jtvnw",
    "live-video",
    "cloudfront",
)
# Ключевые слова в комментариях hosts -> вероятный источник строки.
HOSTS_TOOL_SIGNATURES: dict[str, tuple[str, ...]] = {
    "zapret": ("zapret", "zapret-discord-youtube"),
    "GoodbyeDPI": ("goodbyedpi", "goodbye dpi"),
    "AdGuard": ("adguard", "ad guard"),
    "BlockCheck": ("blockcheck",),
    "SteadyFlow": ("steadyflow",),
    "Pi-hole": ("pi-hole", "pihole"),
    "Ручная блокировка": ("manual", "block", "блокир"),
}
DEFAULT_HOSTS_PATHS: dict[str, str] = {
    "nt": r"C:\Windows\System32\drivers\etc\hosts",
    "posix": "/etc/hosts",
}

# ----------------------------------------------------- антивирусы и процессы
ANTIVIRUS_ISSUERS: tuple[str, ...] = (
    "Kaspersky",
    "ESET",
    "Avast",
    "BitDefender",
    "Norton",
    "McAfee",
    "AVG",
    "Dr.Web",
    "Doctor Web",
    "AO Kaspersky Lab",
)
AV_HTTPS_INSTRUCTIONS: dict[str, str] = {
    "Kaspersky": "Настройки → Сетевые настройки → «Проверка защищённых соединений» → Не проверять / добавить twitch.tv в исключения.",
    "ESET": "Дополнительные настройки → WEB и электронная почта → SSL/TLS → исключения для twitch.tv и *.ttvnw.net.",
    "Avast": "Настройки → Защита → Основные компоненты → Веб-экран → исключения HTTPS-сканирования.",
    "BitDefender": "Защита → Онлайн-угрозы → Настройки → Scan SSL → Off, либо добавьте исключения.",
    "Norton": "Settings → Firewall → Intrusion Prevention → исключите twitch.tv из HTTPS-сканирования.",
    "McAfee": "Настройки → Защита в реальном времени → Веб-защита → исключения SSL.",
    "AVG": "Настройки → Основные компоненты → Веб-экран → исключения HTTPS.",
    "Dr.Web": "Настройки → Защита → Проверка SSL/TLS → добавить домены Twitch в исключения.",
}
AV_HTTPS_INSTRUCTIONS_EN: dict[str, str] = {
    "Kaspersky": "Settings → Network → Encrypted connections scanning → Do not scan / add twitch.tv to exclusions.",
    "ESET": "Advanced setup → Web and email → SSL/TLS → add exclusions for twitch.tv and *.ttvnw.net.",
    "Avast": "Settings → Protection → Core Shields → Web Shield → HTTPS scanning exclusions.",
    "BitDefender": "Protection → Online Threat Prevention → Scan SSL → Off, or add exclusions.",
    "Norton": "Settings → Firewall → Intrusion Prevention → exclude twitch.tv from HTTPS scanning.",
    "McAfee": "Settings → Real-Time Protection → Web protection → SSL exclusions.",
    "AVG": "Settings → Core Shields → Web Shield → HTTPS scanning exclusions.",
    "Dr.Web": "Settings → Protection → SSL/TLS scanning → add Twitch domains to exclusions.",
}

# Категория -> (читаемое имя, шаблоны имён процессов).
PROCESS_SIGNATURES: dict[str, tuple[str, tuple[str, ...]]] = {
    "antivirus": (
        "Антивирусы",
        ("avp", "kaspersky", "ekrn", "egui", "eset", "avast", "avg", "bdagent", "vsserv",
         "bitdefender", "norton", "mcafee", "mfe", "drweb", "spideragent", "msmpeng"),
    ),
    "vpn": (
        "VPN-клиенты",
        ("openvpn", "wireguard", "warp", "cloudflared", "nordvpn", "expressvpn",
         "protonvpn", "psiphon", "lantern", "v2ray", "xray", "sing-box", "mullvad"),
    ),
    "dpi": (
        "DPI-обход",
        ("goodbyedpi", "zapret", "steadyflow", "blockcheck", "byedpi", "spoofdpi", "dpi"),
    ),
    "proxy": (
        "Прокси / MITM",
        ("proxifier", "charles", "fiddler", "mitmproxy", "mitmdump", "burp", "proxycap",
         "squid", "clash", "nekoray"),
    ),
    "blocker": (
        "Блокировщики рекламы / DNS",
        ("adguard", "pi-hole", "pihole", "nextdns", "dnscrypt", "yogaDNS", "simplewall"),
    ),
}
# Программы, которые безопасно предлагать закрыть (исключаем антивирусы и системные).
SAFE_TO_TERMINATE: frozenset[str] = frozenset({"dpi", "proxy", "vpn"})

BROWSER_PATHS: dict[str, tuple[str, ...]] = {
    "Google Chrome": (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ),
    "Microsoft Edge": (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ),
    "Mozilla Firefox": (
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ),
    "Opera": (r"C:\Program Files\Opera\opera.exe",),
    "Brave": (r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",),
}

BLOCK_PAGE_MARKERS: tuple[str, ...] = (
    "доступ к сайту ограничен",
    "сайт заблокирован",
    "ресурс заблокирован",
    "роскомнадзор",
    "access denied",
    "access to this site is blocked",
    "your isp has blocked",
    "err_blocked_by",
    "this site can't be reached",
)

# --------------------------------------------------------------------- цвета
@dataclass(frozen=True)
class Palette:
    """Цветовая палитра для QSS и QPainter-виджетов."""

    bg: str = "#1a1a2e"
    bg_deep: str = "#12121f"
    surface: str = "#16213e"
    surface_alt: str = "#1d2a4d"
    border: str = "#2b3663"
    text: str = "#eef1ff"
    text_muted: str = "#98a2c8"
    accent: str = "#9146ff"
    accent_hover: str = "#a970ff"
    accent_dark: str = "#6b2fd6"
    ok: str = "#00ff88"
    warn: str = "#ffa502"
    error: str = "#ff4757"
    info: str = "#54a0ff"


DARK = Palette()
LIGHT = Palette(
    bg="#eef0f7",
    bg_deep="#e2e6f2",
    surface="#ffffff",
    surface_alt="#f4f6fc",
    border="#d3d9ea",
    text="#1b2038",
    text_muted="#626d90",
    accent="#9146ff",
    accent_hover="#7f31ee",
    accent_dark="#6b2fd6",
    ok="#08a866",
    warn="#c47a00",
    error="#e03144",
    info="#2869d6",
)

STATUS_COLORS: dict[str, str] = {
    "ok": DARK.ok,
    "warning": DARK.warn,
    "error": DARK.error,
    "info": DARK.info,
    "skipped": DARK.text_muted,
    "running": DARK.accent,
}

# ------------------------------------------------------------------ размеры
WINDOW_MIN_WIDTH = 400
WINDOW_MIN_HEIGHT = 600
WINDOW_DEFAULT_WIDTH = 1120
WINDOW_DEFAULT_HEIGHT = 720
COMPACT_WIDTH = 400
COMPACT_HEIGHT = 600
SIDEBAR_COLLAPSED = 60
SIDEBAR_EXPANDED = 200
MONITOR_INTERVAL_MINUTES = 5
HISTORY_RETENTION_DAYS = 7
