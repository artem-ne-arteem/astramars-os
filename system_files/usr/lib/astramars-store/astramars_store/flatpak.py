"""Установка, удаление и запуск приложений через flatpak (Flathub).

Ставим в системную установку: в Fedora правило polkit от flatpak разрешает это
администраторам без пароля. Если не вышло — ставим только для текущего пользователя.
"""

import os
import re
import subprocess
import time

FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"
PERCENT = re.compile(r"(\d{1,3})\s?%")


class FlatpakError(Exception):
    pass


def _explain(text):
    t = text.lower()
    if "not authorized" in t or "authentication" in t or "polkit" in t:
        return "нет прав на установку"
    if "no remote refs found" in t or "nothing matches" in t:
        return "приложение не найдено во Flathub"
    if "could not resolve" in t or "couldn't resolve" in t or "timeout" in t or "network" in t:
        return "нет связи с Flathub — проверьте интернет или VPN"
    if "no space" in t:
        return "не хватает места на диске"
    last = [l for l in text.strip().splitlines() if l.strip()]
    return last[-1][:200] if last else "неизвестная ошибка flatpak"


class Flatpak:
    def _run(self, *args, timeout=120):
        return subprocess.run(["flatpak", *args], capture_output=True, text=True, timeout=timeout)

    def ensure_flathub(self):
        self._run("remote-add", "--system", "--if-not-exists", "flathub", FLATHUB)
        if not any("flathub" in l for l in self._run("remotes", "--system", "--columns=name").stdout.splitlines()):
            self._run("remote-add", "--user", "--if-not-exists", "flathub", FLATHUB)

    def refresh_appstream(self):
        """Свежий список приложений Flathub (несколько мегабайт)."""
        self._run("update", "--appstream", "--system", "flathub", timeout=600)

    def installed(self):
        p = self._run("list", "--app", "--columns=application")
        return {l.strip() for l in p.stdout.splitlines() if l.strip()}

    def install(self, app_id, on_progress):
        last = ""
        for scope in ("--system", "--user"):
            ok, last = self._stream(["install", "-y", "--noninteractive", scope, "flathub", app_id], on_progress)
            if ok:
                return
            if "нет прав" not in _explain(last):
                break
        raise FlatpakError(_explain(last))

    def uninstall(self, app_id, on_progress):
        ok, out = self._stream(["uninstall", "-y", "--noninteractive", app_id], on_progress)
        if not ok:
            raise FlatpakError(_explain(out))

    def updates(self):
        """Приложения, для которых во Flathub есть новая версия (системные и пользовательские)."""
        found = set()
        for scope in ("--system", "--user"):
            p = self._run("remote-ls", scope, "--updates", "--app", "--columns=application", timeout=300)
            if p.returncode == 0:
                found |= {l.strip() for l in p.stdout.splitlines() if l.strip() and "." in l}
        return found

    def update(self, app_id, on_progress):
        """app_id=None — обновить всё (приложения и среды выполнения)."""
        args = ["update", "-y", "--noninteractive"] + ([app_id] if app_id else [])
        ok, out = self._stream(args, on_progress)
        if not ok:
            raise FlatpakError(_explain(out))

    def launch(self, app_id):
        subprocess.Popen(["flatpak", "run", app_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

    def _stream(self, args, on_progress):
        """Запускает flatpak и передаёт проценты из его вывода (строки разделяются \\r и \\n)."""
        proc = subprocess.Popen(["flatpak", *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env=dict(os.environ, LC_ALL="C"))
        out, buf = [], b""
        while True:
            chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            parts = re.split(rb"[\r\n]", buf)
            buf = parts.pop()
            for raw in parts:
                line = raw.decode("utf-8", "replace")
                out.append(line)
                m = PERCENT.search(line)
                if m:
                    on_progress(min(100, int(m.group(1))))
        proc.wait()
        return proc.returncode == 0, "\n".join(out[-40:])


class FakeFlatpak:
    """Режим разработки (ASTRAMARS_STORE_DEV=1): без flatpak, установка «понарошку»."""

    def __init__(self):
        self._installed = {"org.telegram.desktop", "org.mozilla.firefox", "org.libreoffice.LibreOffice"}
        self._updated = set()

    def ensure_flathub(self):
        pass

    def refresh_appstream(self):
        pass

    def installed(self):
        return set(self._installed)

    def install(self, app_id, on_progress):
        for p in range(0, 101, 10):
            on_progress(p)
            time.sleep(0.12)
        self._installed.add(app_id)

    def updates(self):
        return {i for i in ("org.telegram.desktop", "org.mozilla.firefox") if i in self._installed} - self._updated

    def update(self, app_id, on_progress):
        for p in range(0, 101, 20):
            on_progress(p)
            time.sleep(0.1)
        self._updated |= {app_id} if app_id else set(self._installed)

    def uninstall(self, app_id, on_progress):
        on_progress(50)
        time.sleep(0.3)
        self._installed.discard(app_id)

    def launch(self, app_id):
        pass


def create():
    return FakeFlatpak() if os.environ.get("ASTRAMARS_STORE_DEV") else Flatpak()
