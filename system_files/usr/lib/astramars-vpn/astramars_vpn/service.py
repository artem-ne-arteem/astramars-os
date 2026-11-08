"""Управление ядром sing-box через системную службу astramars-vpn@ПОЛЬЗОВАТЕЛЬ.service.

Служба запускается от root с ограниченными правами (только сеть), чтобы работал режим VPN (TUN).
Запуск и остановка без пароля разрешены администраторам правилом polkit."""

import getpass
import json
import os
import subprocess
import time

from . import store

SINGBOX = os.environ.get("ASTRAMARS_VPN_SINGBOX", "/usr/libexec/astramars-vpn/sing-box")


class ServiceError(Exception):
    pass


def _explain(stderr: str) -> str:
    text = (stderr or "").strip()
    if "Access denied" in text or "authentication required" in text.lower():
        return "Нет прав на управление VPN: учётная запись должна быть администратором."
    if "not found" in text or "not loaded" in text:
        return "Служба VPN не найдена. Обновите систему: sudo bootc upgrade"
    return text or "Неизвестная ошибка systemd"


class SystemdService:
    def __init__(self):
        self.user = getpass.getuser()
        self.unit = f"astramars-vpn@{self.user}.service"
        self.config_path = os.path.join(store.config_dir(), "singbox.json")

    def _systemctl(self, *args, check=True):
        p = subprocess.run(["systemctl", *args], capture_output=True, text=True, timeout=40)
        if check and p.returncode != 0:
            raise ServiceError(_explain(p.stderr))
        return p

    def write_config(self, config: dict) -> None:
        store.write_private(self.config_path, json.dumps(config, ensure_ascii=False, indent=2))

    def check_config(self):
        try:
            p = subprocess.run([SINGBOX, "check", "-c", self.config_path],
                               capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return False, "ядро sing-box не установлено"
        return p.returncode == 0, (p.stderr or p.stdout).strip()[-400:]

    def restart(self) -> None:
        self._systemctl("restart", self.unit)

    def stop(self) -> None:
        self._systemctl("stop", self.unit)

    def is_active(self) -> bool:
        return self._systemctl("is-active", "--quiet", self.unit, check=False).returncode == 0

    def active_since(self) -> float:
        """Время (unix) включения службы."""
        p = self._systemctl("show", "-p", "ActiveEnterTimestampMonotonic", "--value", self.unit, check=False)
        try:
            mono = int(p.stdout.strip()) / 1e6
            with open("/proc/uptime", encoding="ascii") as f:
                uptime = float(f.read().split()[0])
            return time.time() - (uptime - mono)
        except (ValueError, OSError):
            return time.time()

    def last_error(self) -> str:
        p = subprocess.run(["journalctl", "-u", self.unit, "-n", "40", "--no-pager", "-o", "cat"],
                           capture_output=True, text=True, timeout=10)
        lines = [l for l in p.stdout.splitlines() if "ERROR" in l or "FATAL" in l]
        return lines[-1].split("]", 1)[-1].strip() if lines else ""

    def refresh_system_proxy(self) -> None:
        """Сразу применить системный прокси (иначе astramars-proxy сделает это за 30 секунд)."""
        subprocess.run(["systemctl", "start", "--no-block", "astramars-proxy.service"],
                       capture_output=True, timeout=10)


class FakeService:
    """Режим разработки (ASTRAMARS_VPN_DEV=1): без systemd и sing-box."""

    def __init__(self):
        self.active = False
        self.since = 0.0
        self.config_path = os.path.join(store.config_dir(), "singbox.json")

    def write_config(self, config):
        store.write_private(self.config_path, json.dumps(config, ensure_ascii=False, indent=2))

    def check_config(self):
        return True, ""

    def restart(self):
        time.sleep(0.6)
        self.active, self.since = True, time.time()

    def stop(self):
        self.active = False

    def is_active(self):
        return self.active

    def active_since(self):
        return self.since

    def last_error(self):
        return ""

    def refresh_system_proxy(self):
        pass


def create():
    return FakeService() if os.environ.get("ASTRAMARS_VPN_DEV") else SystemdService()
