"""Обновления системы AstraMars OS для магазина.

Сама работа идёт от root в службах astramars-update-check/apply.service (см. /usr/libexec/astramars-update),
магазин только запускает их и читает /run/astramars-update/status.json.
"""

import datetime as dt
import json
import os
import subprocess
import time

STATUS = os.environ.get("ASTRAMARS_UPDATE_STATUS", "/run/astramars-update/status.json")
UNIT = "astramars-update-{}.service"

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]


class UpdateError(Exception):
    pass


def os_name():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return "AstraMars OS"


def human_date(iso):
    try:
        d = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone()
    except ValueError:
        return ""
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def human_time(iso):
    try:
        return dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone().strftime("%H:%M")
    except ValueError:
        return ""


def summarize(raw, running):
    """Состояние для интерфейса из status.json и того, работает ли служба."""
    booted = raw.get("booted") or {}
    staged = raw.get("staged")
    info = {
        "name": os_name(),
        "built": human_date(booted.get("timestamp")) if booted.get("timestamp") else "",
        "line": "",
        "error": "",
        "checked": human_time(raw["checked_at"]) if raw.get("checked_at") else "",
    }
    if running == "apply":
        info.update(state="downloading", line=raw.get("line") or "Скачиваю обновление…")
    elif running == "check":
        info.update(state="checking")
    elif staged and staged.get("digest") != booted.get("digest"):
        info.update(state="ready", newBuilt=human_date(staged.get("timestamp")))
    elif raw.get("error"):
        info.update(state="error", error=raw["error"])
    elif raw.get("available"):
        info.update(state="available")
    elif raw.get("checked_at"):
        info.update(state="current")
    else:
        info.update(state="unknown")
    return info


class SystemUpdates:
    def read(self):
        try:
            with open(STATUS, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def running(self):
        for kind in ("apply", "check"):
            p = subprocess.run(["systemctl", "is-active", "--quiet", UNIT.format(kind)])
            if p.returncode == 0:
                return kind
        return ""

    def start(self, kind):
        p = subprocess.run(["systemctl", "start", "--no-block", UNIT.format(kind)],
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            text = p.stderr.strip()
            if "Access denied" in text or "authentication" in text.lower():
                raise UpdateError("нет прав: обновлять систему может только администратор")
            if "not found" in text:
                raise UpdateError("служба обновлений не найдена — нужна новая версия образа")
            raise UpdateError(text or "не удалось запустить обновление")

    def reboot(self):
        subprocess.Popen(["systemctl", "reboot"])


class FakeSystemUpdates:
    """Режим разработки: проверка находит обновление, скачивание занимает пару секунд."""

    def __init__(self):
        self._raw = {"booted": {"timestamp": "2026-11-07T21:39:51Z", "digest": "sha256:a"},
                     "checked_at": "2026-11-08T10:05:00Z"}
        self._job, self._until = "", 0.0

    def read(self):
        if self._job and time.time() > self._until:
            if self._job == "check":
                self._raw.update(available={"digest": "sha256:b"}, checked_at=dt.datetime.now(dt.timezone.utc).isoformat())
            else:
                self._raw.update(staged={"timestamp": "2026-11-08T16:00:00Z", "digest": "sha256:b"}, available=None)
            self._job = ""
        if self._job == "apply":
            self._raw["line"] = "Fetching layer 7/12 (412 MB)"
        return dict(self._raw, phase="downloading" if self._job == "apply" else "idle")

    def running(self):
        return self._job if self._job and time.time() <= self._until else ""

    def start(self, kind):
        self._job, self._until = kind, time.time() + (1.5 if kind == "check" else 3.0)

    def reboot(self):
        pass


def create():
    return FakeSystemUpdates() if os.environ.get("ASTRAMARS_STORE_DEV") else SystemUpdates()
