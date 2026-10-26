"""Исправление №8: инструкция по отключению HTTPS-сканирования антивируса.

Мы намеренно НЕ трогаем настройки антивируса автоматически: вмешательство в
защиту ПО должно выполняться пользователем вручную. FixResult содержит
пошаговую инструкцию для конкретного вендора.
"""
from __future__ import annotations

from src.config.constants import AV_HTTPS_INSTRUCTIONS, AV_HTTPS_INSTRUCTIONS_EN
from src.config.i18n import i18n
from src.core.fixes.base_fix import BaseFix, FixResult


class SSLFix(BaseFix):
    id = "ssl"
    title_ru = "Отключить HTTPS-сканирование антивируса"
    title_en = "Disable antivirus HTTPS scanning"
    description_ru = "Добавить twitch.tv и *.ttvnw.net в исключения проверки SSL в вашем антивирусе (пошаговая инструкция)."
    description_en = "Add twitch.tv and *.ttvnw.net to SSL inspection exclusions in your antivirus (step-by-step guide)."
    requires_admin = False

    def apply(self, dry_run: bool = False) -> FixResult:
        vendor = str(self.context.get("antivirus", "Kaspersky")) if self.context else "Kaspersky"
        instruction_ru = AV_HTTPS_INSTRUCTIONS.get(vendor, AV_HTTPS_INSTRUCTIONS["Kaspersky"])
        instruction_en = AV_HTTPS_INSTRUCTIONS_EN.get(vendor, AV_HTTPS_INSTRUCTIONS_EN["Kaspersky"])
        details = [
            f"detected vendor: {vendor}",
            f"issuer: {self.context.get('issuer', 'n/a') if self.context else 'n/a'}",
        ]
        if i18n.language == "ru":
            details += [instruction_ru, "Домены для исключений: twitch.tv, *.twitch.tv, *.ttvnw.net, *.jtvnw.net"]
        else:
            details += [instruction_en, "Exclusion domains: twitch.tv, *.twitch.tv, *.ttvnw.net, *.jtvnw.net"]
        details.append("After changing settings, restart the browser and run diagnostics again.")
        if self.backup:
            self.backup.manifest["ssl_instruction"] = {
                "vendor": vendor, "instruction_ru": instruction_ru, "instruction_en": instruction_en,
            }
            self.backup._flush()
        return self.result(
            True,
            f"Инструкция для {vendor} подготовлена",
            f"Instructions for {vendor} prepared",
            details=details,
        )
