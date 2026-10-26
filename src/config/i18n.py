"""Простая двуязычная локализация (RU по умолчанию / EN).

Все статические строки интерфейса лежат здесь. Смена языка в настройках
рассылает сигнал ``language_changed``; страницы реализуют ``retranslate_ui``.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

TR: dict[str, tuple[str, str]] = {
    # (Русский, English) — кортежи, чтобы случайная опечатка в ключе была видна сразу
    "app.subtitle": ("Диагностика подключения к Twitch", "Twitch connection diagnostics"),
    "nav.dashboard": ("Главная", "Dashboard"),
    "nav.diagnostics": ("Диагностика", "Diagnostics"),
    "nav.autofix": ("Авто-исправление", "Auto-fix"),
    "nav.report": ("Отчёт", "Report"),
    "nav.settings": ("Настройки", "Settings"),
    "nav.expand": ("Развернуть меню", "Expand menu"),
    "nav.collapse": ("Свернуть меню", "Collapse menu"),
    "title.minimize": ("Свернуть", "Minimize"),
    "title.maximize": ("Развернуть", "Maximize"),
    "title.restore": ("Восстановить", "Restore"),
    "title.compact": ("Компактное окно", "Compact window"),
    "title.fullscreen": ("Полноэкранный режим (F11)", "Fullscreen (F11)"),
    "title.close": ("Закрыть", "Close"),
    "common.run_diagnostics": ("Запустить полную диагностику", "Run full diagnostics"),
    "common.quick_fix": ("Быстрое исправление", "Quick Fix"),
    "common.copy": ("Копировать", "Copy"),
    "common.save": ("Сохранить в файл", "Save to file"),
    "common.share": ("Поделиться", "Share"),
    "common.fix": ("Исправить", "Fix"),
    "common.skip": ("Пропустить", "Skip"),
    "common.fix_all": ("Исправить всё", "Fix all"),
    "common.cancel": ("Отмена", "Cancel"),
    "common.details": ("Подробнее", "Details"),
    "common.back": ("Назад", "Back"),
    "common.ok": ("OK", "OK"),
    "common.warning": ("Внимание", "Warning"),
    "common.error": ("Ошибка", "Error"),
    "common.skipped": ("Пропущено", "Skipped"),
    "common.running": ("Выполняется…", "Running…"),
    "common.not_checked": ("Не проверялось", "Not checked"),
    "common.admin_required": ("Требуются права администратора", "Administrator rights required"),
    "common.restart_admin": ("Перезапустить от имени администратора", "Restart as administrator"),
    "common.close_app": ("Закрыть приложение", "Quit application"),
    "common.show": ("Показать окно", "Show window"),
    "common.check_now": ("Проверить сейчас", "Check now"),
    "common.yes": ("Да", "Yes"),
    "common.no": ("Нет", "No"),
    "common.done": ("Готово", "Done"),
    "common.failed": ("Не удалось", "Failed"),
    "common.seconds": ("сек", "s"),
    "common.system": ("Система", "System"),
    "common.saved": ("Сохранено", "Saved"),
    "common.copied": ("Скопировано в буфер обмена", "Copied to clipboard"),
    # Dashboard
    "dashboard.title": ("Обзор подключения", "Connection overview"),
    "dashboard.subtitle": ("Проверяем всё, что может мешать Twitch", "Everything that can break Twitch, in one place"),
    "dashboard.status_ok": ("Twitch доступен", "Twitch is reachable"),
    "dashboard.status_problem": ("Обнаружены проблемы", "Problems detected"),
    "dashboard.status_unknown": ("Диагностика ещё не запускалась", "Diagnostics have not run yet"),
    "dashboard.status_checking": ("Проверка соединения…", "Checking connection…"),
    "dashboard.status_ok_hint": ("Все ключевые проверки пройдены. Можно смотреть стримы!", "All key checks passed. Happy streaming!"),
    "dashboard.status_problem_hint": ("Откройте «Авто-исправление», чтобы устранить найденные проблемы.", "Open Auto-fix to resolve detected issues."),
    "dashboard.status_unknown_hint": ("Нажмите кнопку ниже, чтобы проверить hosts, DNS, SSL, прокси и ещё 8 параметров.", "Press the button below to check hosts, DNS, SSL, proxy and 8 more subsystems."),
    "dashboard.last_check": ("Последняя проверка: {}", "Last check: {}"),
    "dashboard.never": ("никогда", "never"),
    "dashboard.cards": ("Быстрый статус", "Quick status"),
    "dashboard.availability": ("Доступность", "Availability"),
    "dashboard.period_24h": ("24 часа", "24 hours"),
    "dashboard.period_7d": ("7 дней", "7 days"),
    "dashboard.no_history": ("Пока нет данных мониторинга", "No monitoring data yet"),
    "dashboard.quick_fix_hint": ("Одна кнопка: flush DNS → hosts → Winsock → кэш браузера", "One click: flush DNS → hosts → Winsock → browser cache"),
    # Dashboard mini-cards (check id -> название)
    "card.dns": ("DNS", "DNS"),
    "card.hosts": ("Hosts файл", "Hosts file"),
    "card.ssl": ("SSL сертификат", "SSL certificate"),
    "card.proxy": ("Прокси", "Proxy"),
    "card.firewall": ("Файрвол", "Firewall"),
    "card.process": ("Конфликты ПО", "Software conflicts"),
    "card.tip": ("Нажмите для подробностей", "Click for details"),
    # Diagnostics
    "diagnostics.title": ("Диагностика", "Diagnostics"),
    "diagnostics.subtitle": ("13 проверок, от hosts до Twitch API", "13 checks, from hosts to the Twitch API"),
    "diagnostics.start": ("Запустить проверку", "Start checks"),
    "diagnostics.stop": ("Остановить", "Stop"),
    "diagnostics.progress": ("Прогресс", "Progress"),
    "diagnostics.log": ("Журнал проверок", "Check log"),
    "diagnostics.clear_log": ("Очистить лог", "Clear log"),
    "diagnostics.completed": ("Готово: {} проверок за {}", "Done: {} checks in {}"),
    "diagnostics.empty": ("Проверки ещё не запускались. Нажмите «Запустить проверку».", "No checks yet. Press 'Start checks'."),
    "diagnostics.expand_hint": ("Нажмите на карточку, чтобы раскрыть детали", "Click a card to expand details"),
    # Auto-fix
    "autofix.title": ("Авто-исправление", "Auto-fix"),
    "autofix.subtitle": ("Исправляем только то, что вы подтвердите", "Only fixes you explicitly approve"),
    "autofix.no_problems": ("Проблем не найдено", "No problems found"),
    "autofix.no_problems_hint": ("Сначала запустите диагностику — мы соберём список проблем автоматически.", "Run diagnostics first — the problem list is built automatically."),
    "autofix.restore_point": ("Создать точку восстановления перед изменением", "Create a restore point before changes"),
    "autofix.backup_note": ("Все изменяемые файлы и параметры реестра сначала копируются в папку бэкапов.", "All modified files and registry values are backed up first."),
    "autofix.admin_banner": ("Некоторые исправления требуют прав администратора (UAC).", "Some fixes require administrator rights (UAC)."),
    "autofix.confirm_title": ("Подтвердите исправление", "Confirm the fix"),
    "autofix.confirm_text": ("Применить исправление «{}»? Будет создана резервная копия.", "Apply fix '{}'? A backup will be created first."),
    "autofix.confirm_all": ("Применить все предложенные исправления ({} шт.)? Все изменения будут сохранены в бэкап.", "Apply all suggested fixes ({})? All changes will be backed up."),
    "autofix.fixed": ("Исправлено", "Fixed"),
    "autofix.skipped": ("Пропущено", "Skipped"),
    "autofix.running": ("Применяем исправления…", "Applying fixes…"),
    "autofix.quick_running": ("Быстрое исправление…", "Quick fixing…"),
    "autofix.quick_done": ("Быстрое исправление завершено", "Quick fix finished"),
    "autofix.need_admin": ("Для этого исправления нужны права администратора. Перезапустите приложение от имени администратора.", "This fix needs administrator rights. Restart the app as administrator."),
    # Report
    "report.title": ("Отчёт", "Report"),
    "report.subtitle": ("Готов к отправке в поддержку или на форум", "Ready for support or a forum post"),
    "report.empty": ("Отчёт появится после первой диагностики.", "The report appears after the first diagnostics run."),
    "report.share_done": ("Короткая версия отчёта скопирована", "Short report copied to clipboard"),
    "report.save_dialog": ("Сохранить отчёт", "Save report"),
    "report.filters": ("Markdown (*.md);;HTML (*.html);;Text (*.txt)", "Markdown (*.md);;HTML (*.html);;Text (*.txt)"),
    # Settings
    "settings.title": ("Настройки", "Settings"),
    "settings.subtitle": ("Поведение приложения и внешний вид", "Application behaviour and appearance"),
    "settings.general": ("Основные", "General"),
    "settings.autostart": ("Автозапуск при старте Windows", "Launch at Windows startup"),
    "settings.language": ("Язык интерфейса", "Interface language"),
    "settings.theme": ("Тема", "Theme"),
    "settings.dark": ("Тёмная", "Dark"),
    "settings.light": ("Светлая", "Light"),
    "settings.notifications": ("Уведомления в системном трее", "System tray notifications"),
    "settings.monitoring": ("Фоновый мониторинг Twitch", "Background Twitch monitoring"),
    "settings.monitor_interval": ("Интервал проверки (минуты)", "Check interval (minutes)"),
    "settings.history_days": ("Хранить историю (дней)", "Keep history (days)"),
    "settings.about": ("О программе", "About"),
    "settings.version": ("Версия", "Version"),
    "settings.github": ("Исходный код на GitHub", "Source code on GitHub"),
    "settings.logs": ("Открыть папку с логами", "Open log folder"),
    "settings.reset": ("Сбросить настройки", "Reset settings"),
    "settings.restart_hint": ("Язык и тема применяются сразу.", "Language and theme apply immediately."),
    # Tray / monitor
    "monitor.down_title": ("Twitch недоступен", "Twitch is unreachable"),
    "monitor.down_msg": ("Потеряно соединение с Twitch. Откройте TwitchFix для диагностики.", "Lost connection to Twitch. Open TwitchFix to diagnose."),
    "monitor.up_title": ("Связь восстановлена", "Connection restored"),
    "monitor.up_msg": ("Twitch снова доступен.", "Twitch is reachable again."),
    "monitor.check_ok": ("Twitch доступен", "Twitch is reachable"),
    "monitor.check_fail": ("Twitch недоступен — запустите диагностику", "Twitch unreachable — run diagnostics"),
    # Report sections
    "report.section_summary": ("Сводка", "Summary"),
    "report.section_system": ("Система", "System"),
    "report.section_checks": ("Результаты проверок", "Check results"),
    "report.section_fixes": ("Выполненные исправления", "Applied fixes"),
    "report.section_history": ("История доступности", "Availability history"),
    "report.generated": ("Сформирован", "Generated"),
    "report.status": ("Общий статус", "Overall status"),
    "report.issues": ("Проблем: {}", "Issues: {}"),
    "report.disclaimer": ("Отчёт не содержит паролей, токенов и приватных данных. Проверьте его перед публикацией.", "The report contains no passwords or tokens. Review it before publishing."),
}


class I18n(QObject):
    """Глобальный переводчик. Работает без создания QApplication."""

    language_changed = pyqtSignal(str)

    def __init__(self, language: str = "ru") -> None:
        super().__init__()
        self._language = language if language in ("ru", "en") else "ru"

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        language = language if language in ("ru", "en") else "ru"
        if language != self._language:
            self._language = language
            self.language_changed.emit(language)

    def tr(self, key: str, *args: object) -> str:
        """Вернуть перевод ключа; ``{}``-плейсхолдеры заполняются ``*args``."""
        index = 0 if self._language == "ru" else 1
        pair = TR.get(key)
        text = pair[index] if pair else key
        if args:
            try:
                text = text.format(*args)
            except (IndexError, ValueError, KeyError):
                pass
        return text

    def pick(self, ru: str, en: str) -> str:
        """Выбрать строку по текущему языку (для результатов проверок)."""
        return ru if self._language == "ru" else en


i18n = I18n()
