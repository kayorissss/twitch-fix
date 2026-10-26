# Changelog

All notable changes to TwitchFix are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-10-26

### Added
- 13 independent diagnostics modules (hosts, DNS, TCP, SSL, HTTP, time, proxy, firewall, adapter, processes, ping/traceroute, browser, Twitch API/video/chat).
- 9 auto-fixes with mandatory backups, restore-point support and UAC elevation.
- Quick Fix: flush DNS → hosts cleanup → Winsock reset → browser cache.
- Professional frameless UI: custom title bar, collapsible sidebar, animated page transitions, gradient progress bar, pulsing status indicators, terminal log, toasts.
- Dark/light QSS themes, RU/EN localization, compact 400×600 mode and F11 fullscreen.
- Background tray monitoring (5-minute interval), 24h/7d availability history chart.
- Markdown/HTML/TXT report generator, clipboard copy and short share text.
- PyInstaller one-file build (`build.py`, `build.bat`) and GitHub Actions release workflow.
- 44 platform-independent unit tests.

### Notes
- Windows 10/11 is the target platform; Windows-specific checks are skipped on other systems.
- The app is not affiliated with Twitch Interactive, Inc.
- Release `v1.0.0` ships a 39.3 MB (41,259,969 bytes) one-file `TwitchFix.exe` built by GitHub Actions.
