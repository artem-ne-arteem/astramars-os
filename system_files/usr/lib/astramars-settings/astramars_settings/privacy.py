"""Приватность: что система отправляет (ничего), и кто сейчас использует микрофон и камеру."""

import json
import os
import re

from .util import DEV, sh, spawn

# Наши службы и свои программы ничего о вас не отправляют. Здесь — честный список того,
# что в Fedora и KDE могло бы что-то отправлять, и в каком оно состоянии.


def telemetry():
    if DEV:
        return [{"name": "Счётчик установок Fedora (countme)", "state": "выключен", "ok": True},
                {"name": "Отчёты KDE о работе программ", "state": "выключены", "ok": True},
                {"name": "Отчёты о сбоях", "state": "только когда вы сами решите отправить", "ok": True}]
    code, out = sh(["systemctl", "is-enabled", "rpm-ostree-countme.timer"])
    countme_off = out.strip() in ("disabled", "masked", "") or code == 4 or "No such" in out
    code, fb = sh(["kreadconfig6", "--file", "KDE/UserFeedback.conf", "--group", "UserFeedback",
                   "--key", "ApplicationTelemetry"])
    kde_off = fb.strip() in ("", "NoTelemetry")
    return [
        {"name": "Счётчик установок Fedora (countme)", "state": "выключен" if countme_off else "включён",
         "ok": countme_off},
        {"name": "Отчёты KDE о работе программ", "state": "выключены" if kde_off else "включены",
         "ok": kde_off},
        {"name": "Отчёты о сбоях", "state": "только когда вы сами решите отправить", "ok": True},
    ]


def microphone_users():
    """Программы, которые прямо сейчас записывают звук с микрофона."""
    if DEV:
        return ["Telegram"]
    code, out = sh(["pactl", "-f", "json", "list", "source-outputs"])
    if code != 0:
        return []
    try:
        items = json.loads(out)
    except ValueError:
        return []
    names = []
    for item in items:
        props = item.get("properties") or {}
        if props.get("stream.monitor") == "true" or "peak" in (props.get("media.name") or "").lower():
            continue   # индикаторы громкости, а не запись
        name = props.get("application.name") or props.get("application.process.binary") or "программа"
        if name not in names:
            names.append(name)
    return names


def camera_users():
    """Программы, у которых сейчас открыта камера (/dev/video*)."""
    if DEV:
        return []
    names = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        fd_dir = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(os.path.join(fd_dir, fd))
            except OSError:
                continue
            if re.fullmatch(r"/dev/video\d+", target):
                try:
                    comm = open(f"/proc/{pid}/comm").read().strip()
                except OSError:
                    comm = "программа"
                if comm not in ("pipewire", "wireplumber") and comm not in names:
                    names.append(comm)
                break
    # Камера через PipeWire: сам pipewire держит устройство, когда кто-то смотрит в камеру
    if not names:
        code, out = sh(["pw-dump"], timeout=10)
        if code == 0:
            try:
                for obj in json.loads(out):
                    props = ((obj.get("info") or {}).get("props")) or {}
                    if props.get("media.class") == "Video/Source" and (obj.get("info") or {}).get("state") == "running":
                        names.append("приложение через PipeWire")
                        break
            except ValueError:
                pass
    return names


def open_permissions():
    """Разрешения приложений Flatpak (камера, микрофон, файлы) — в Настройках KDE."""
    spawn("systemsettings", "kcm_flatpak")
