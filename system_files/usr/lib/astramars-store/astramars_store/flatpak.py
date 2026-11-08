"""Установка, удаление и запуск приложений через flatpak (Flathub).

Ставим в системную установку: в Fedora правило polkit от flatpak разрешает это
администраторам без пароля. Если не вышло — ставим только для текущего пользователя.
"""

import os
import re
import select
import subprocess
import time

FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][0-9A-Za-z]|\x1b[=>78]")
PERCENT = re.compile(r"(\d{1,3})\s?%")
STEP = re.compile(r"(?:Installing|Updating|Uninstalling|Downloading)\s+(\d+)/(\d+)")
# Между числом и единицей flatpak ставит неразрывный пробел (в локали C — «?»)
SPEED = re.compile(r"(\d+(?:[.,]\d+)?)[\s ?]*([kKMG])B/s")
UNITS = {"k": "КБ/с", "K": "КБ/с", "M": "МБ/с", "G": "ГБ/с"}


class ProgressParser:
    """Достаёт из вывода flatpak общий процент и скорость.

    Если ставится несколько частей (среда выполнения + приложение), flatpak пишет
    «Installing 2/3… 45%» — считаем общий процент по всем частям. Он не уменьшается.
    """

    def __init__(self):
        self.step, self.steps = 1, 1
        self.percent = 0
        self.speed = ""

    def feed(self, line):
        line = ANSI.sub("", line)
        changed = False
        m = STEP.search(line)
        if m:
            self.step, self.steps = int(m.group(1)), max(1, int(m.group(2)))
        m = SPEED.search(line)
        if m:
            value = m.group(1).replace(".", ",")
            speed = f"{value} {UNITS[m.group(2)]}"
            changed |= speed != self.speed
            self.speed = speed
        m = PERCENT.search(line)
        if m:
            part = min(100, int(m.group(1)))
            overall = int(((self.step - 1) + part / 100) / self.steps * 100)
            if overall > self.percent:
                self.percent = overall
                changed = True
        return changed


class FlatpakError(Exception):
    pass


def _explain(text):
    t = text.lower()
    if "not authorized" in t or "not allowed" in t or "authentication" in t or "polkit" in t:
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
    def __init__(self):
        self.progress_samples = []   # строки прогресса flatpak — для проверок и отладки

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
            ok, last = self._stream(["install", "-y", scope, "flathub", app_id], on_progress)
            if ok:
                return
            # Нет связи или места — пользовательская установка не поможет. Остальное
            # (нет прав, Flathub не подключён к системе) — пробуем поставить только для себя.
            reason = _explain(last)
            if reason.startswith("нет связи") or reason.startswith("не хватает места"):
                break
        raise FlatpakError(_explain(last))

    def uninstall(self, app_id, on_progress):
        ok, out = self._stream(["uninstall", "-y", app_id], on_progress)
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
        args = ["update", "-y"] + ([app_id] if app_id else [])
        ok, out = self._stream(args, on_progress)
        if not ok:
            raise FlatpakError(_explain(out))

    def launch(self, app_id):
        subprocess.Popen(["flatpak", "run", app_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

    def _stream(self, args, on_progress):
        """Запускает flatpak в псевдотерминале: только так он показывает проценты и скорость.

        on_progress(процент, подробности) вызывается при каждом изменении.
        """
        import fcntl
        import pty
        import struct
        import termios

        master, slave = pty.openpty()
        # Широкий «терминал», чтобы строка прогресса не обрезалась
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 160, 0, 0))
        env = dict(os.environ, LC_ALL="C.UTF-8", LANG="C.UTF-8", TERM="xterm-256color", COLUMNS="160")
        # Терминал только на выходе: проценты flatpak пишет туда. На входе — пустота,
        # чтобы он не стал спрашивать пароль в терминале и не завис в ожидании.
        proc = subprocess.Popen(["flatpak", *args], stdin=subprocess.DEVNULL, stdout=slave, stderr=slave,
                                env=env, close_fds=True, start_new_session=True)
        os.close(slave)
        parser, out, buf = ProgressParser(), [], b""
        try:
            while True:
                ready, _, _ = select.select([master], [], [], 0.5)
                if not ready:
                    if proc.poll() is not None:
                        break
                    continue
                try:
                    chunk = os.read(master, 4096)
                except OSError:          # EIO: процесс закрыл терминал
                    break
                if not chunk:
                    break
                buf += chunk
                parts = re.split(rb"[\r\n]", buf)
                buf = parts.pop()
                for raw in parts:
                    line = ANSI.sub("", raw.decode("utf-8", "replace")).strip()
                    if line:
                        out.append(line)
                    if "%" in line and len(self.progress_samples) < 40:
                        self.progress_samples.append(repr(line))
                    if parser.feed(line):
                        on_progress(parser.percent, parser.speed)
                # Строка прогресса перерисовывается без перевода строки — разбираем и хвост
                if buf and parser.feed(buf.decode("utf-8", "replace")):
                    on_progress(parser.percent, parser.speed)
        finally:
            os.close(master)
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
            on_progress(p, f"{4 + p % 7},{p % 10} МБ/с")
            time.sleep(0.12)
        self._installed.add(app_id)

    def updates(self):
        return {i for i in ("org.telegram.desktop", "org.mozilla.firefox") if i in self._installed} - self._updated

    def update(self, app_id, on_progress):
        for p in range(0, 101, 20):
            on_progress(p, "8,1 МБ/с")
            time.sleep(0.1)
        self._updated |= {app_id} if app_id else set(self._installed)

    def uninstall(self, app_id, on_progress):
        on_progress(50, "")
        time.sleep(0.3)
        self._installed.discard(app_id)

    def launch(self, app_id):
        pass


def create():
    return FakeFlatpak() if os.environ.get("ASTRAMARS_STORE_DEV") else Flatpak()
