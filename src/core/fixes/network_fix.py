"""Исправления №5–7: сеть (MTU/IPv6), системное время и файрвол.

Все операции требуют UAC и выполняются только в Windows. Перед изменениями
текущие значения (MTU, состояние IPv6-биндинга, правила файрвола) пишутся в
манифест бэкапа.
"""
from __future__ import annotations

from src.core.fixes.base_fix import BaseFix, FixResult
from src.core.fixes.dns_fix import active_adapters
from src.utils.system_info import run_command

RECOMMENDED_MTU = 1400


class NetworkFix(BaseFix):
    id = "network"
    title_ru = "Оптимизировать сеть (MTU / IPv6)"
    title_en = "Optimize network (MTU / IPv6)"
    description_ru = (
        "Установить MTU 1400 для мобильной раздачи и отключить неработающий IPv6 "
        "на активном адаптере. Состояние сохраняется в бэкап."
    )
    description_en = (
        "Set MTU 1400 for mobile tethering and disable broken IPv6 on the active adapter. "
        "The previous state is saved in the backup."
    )
    requires_admin = True
    windows_only = True
    dangerous = True

    def apply(self, dry_run: bool = False) -> FixResult:
        adapters = active_adapters()
        mtu_before = self.context.get("mtu")
        disable_ipv6 = bool(self.context.get("ipv6_broken"))
        details = [
            f"adapters: {', '.join(adapters) or 'none'}",
            f"current MTU: {mtu_before or 'n/a'} -> {RECOMMENDED_MTU}",
            f"disable IPv6 binding: {disable_ipv6}",
        ]
        if self.backup:
            self.backup.manifest["network_before"] = {
                "mtu": mtu_before,
                "adapters": adapters,
                "ipv6_disabled": disable_ipv6,
            }
            self.backup._flush()
        if dry_run:
            return self.result(
                True,
                "MTU и IPv6 будут скорректированы",
                "MTU and IPv6 would be adjusted",
                details=details,
            )
        if not adapters:
            return self.result(False, "Нет активных адаптеров", "No active adapters", details=details)

        for adapter in adapters:
            code, out, err = run_command(
                ["netsh", "interface", "ipv4", "set", "subinterface", adapter,
                 f"mtu={RECOMMENDED_MTU}", "store=persistent"],
                timeout=10,
            )
            details.append(f"MTU {adapter} -> code {code} {(out + err).strip()[:80]}")
            if disable_ipv6:
                script = (
                    "try {{ Disable-NetAdapterBinding -Name '{name}' "
                    "-ComponentID ms_tcpip6 -ErrorAction Stop; 'OK' }} "
                    "catch {{ 'FAIL: ' + $_.Exception.Message }}"
                ).format(name=adapter)
                ps_code, ps_out, _ = run_command(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout=20
                )
                details.append(f"IPv6 {adapter} -> code {ps_code}: {ps_out.strip()[:100]}")
        return self.result(
            True,
            f"MTU={RECOMMENDED_MTU} установлен, IPv6: {'отключён' if disable_ipv6 else 'без изменений'}",
            f"MTU={RECOMMENDED_MTU} set, IPv6: {'disabled' if disable_ipv6 else 'unchanged'}",
            details=details,
            needs_restart=True,
        )


class TimeFix(BaseFix):
    id = "time"
    title_ru = "Синхронизировать системное время"
    title_en = "Synchronize system time"
    description_ru = "Настроить NTP-сервер pool.ntp.org и выполнить принудительную синхронизацию через w32tm."
    description_en = "Configure pool.ntp.org and force time synchronization with w32tm."
    requires_admin = True
    windows_only = True

    def apply(self, dry_run: bool = False) -> FixResult:
        details = [f"detected offset: {self.context.get('offset_seconds', 'n/a')} s"]
        if self.backup:
            self.backup.manifest["time_before"] = {
                "offset_seconds": self.context.get("offset_seconds"),
                "local": self.context.get("local"),
            }
            self.backup._flush()
        if dry_run:
            return self.result(True, "Время будет синхронизировано", "Time would be synchronized", details=details)
        code, out, err = run_command(
            ["w32tm", "/config", "/manualpeerlist:pool.ntp.org", "/syncfromflags:manual", "/update"],
            timeout=15,
        )
        details.append(f"w32tm /config -> {code}: {(out + err).strip()[:120]}")
        sync_code, sync_out, sync_err = run_command(["w32tm", "/resync", "/force"], timeout=20)
        details.append(f"w32tm /resync -> {sync_code}: {(sync_out + sync_err).strip()[:120]}")
        success = sync_code == 0
        return self.result(
            success,
            "Время синхронизировано" if success else "Не удалось синхронизировать время",
            "Time synchronized" if success else "Time synchronization failed",
            details=details,
        )


class FirewallFix(BaseFix):
    id = "firewall"
    title_ru = "Разрешить Twitch в файрволе"
    title_en = "Allow Twitch in firewall"
    description_ru = (
        "Отключить найденные блокирующие правила для Twitch/браузеров и создать "
        "разрешающее исходящее правило для TCP 80/443."
    )
    description_en = (
        "Disable blocking rules targeting Twitch/browsers and create an outbound "
        "allow rule for TCP 80/443."
    )
    requires_admin = True
    windows_only = True
    dangerous = True

    def apply(self, dry_run: bool = False) -> FixResult:
        rules = self.context.get("blocking_rules", []) if self.context else []
        names = [str(rule.get("rule name", "")) for rule in rules if isinstance(rule, dict)]
        names = [name for name in names if name]
        details = [f"blocking rules to disable: {len(names)}"] + [f"  - {name}" for name in names[:10]]
        if self.backup:
            self.backup.manifest["firewall_rules_before"] = rules
            self.backup._flush()
        if dry_run:
            return self.result(
                True,
                f"Будет отключено правил: {len(names)} и создано разрешающее правило",
                f"Would disable {len(names)} rules and add an allow rule",
                details=details,
            )
        for name in names[:20]:
            code, out, err = run_command(
                ["netsh", "advfirewall", "firewall", "set", "rule", f'name={name}', "new", "enable=No"],
                timeout=10,
            )
            details.append(f"disable '{name}' -> {code} {(out + err).strip()[:70]}")
        code, out, err = run_command(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                'name=TwitchFix Allow Twitch', "dir=out", "action=allow",
                "protocol=TCP", "remoteport=80,443", "enable=yes",
            ],
            timeout=10,
        )
        details.append(f"allow rule -> code {code}: {(out + err).strip()[:100]}")
        return self.result(
            code == 0,
            "Правила файрвола обновлены" if code == 0 else "Не удалось создать правило",
            "Firewall rules updated" if code == 0 else "Could not create firewall rule",
            details=details,
        )
