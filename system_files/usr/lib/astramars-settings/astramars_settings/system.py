"""Главная и «Система»: сведения о компьютере, обновления, откат, снимки домашних папок."""

import json
import os
import platform
import re
import shutil
import socket

from .util import DEV, HOME, USER, helper, human, read, sh, spawn

UPDATE_STATUS = "/run/astramars-update/status.json"
SNAP_ROOT = "/var/home/.snapshots"


def os_release():
    data = {}
    for line in read("/usr/lib/os-release").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v.strip().strip('"')
    return data


def _cpu():
    for line in read("/proc/cpuinfo").splitlines():
        if line.startswith("model name"):
            name = line.split(":", 1)[1].strip()
            return re.sub(r"\s+", " ", re.sub(r"\((R|TM)\)|CPU|@.*$|\d+-Core Processor", "", name)).strip()
    return platform.processor() or "—"


def gpus():
    """[{vendor: nvidia|amd|intel|other, name}] по данным ядра и lspci."""
    if DEV:
        return [{"vendor": "nvidia", "name": "NVIDIA GeForce RTX 4060"}]
    found = []
    code, out = sh(["lspci", "-mm"])
    for line in out.splitlines() if code == 0 else []:
        if '"VGA' in line or '"3D' in line or '"Display' in line:
            parts = re.findall(r'"([^"]*)"', line)
            name = " ".join(parts[1:3]) if len(parts) >= 3 else line
            low = name.lower()
            vendor = "nvidia" if "nvidia" in low else "amd" if ("amd" in low or "ati" in low) else \
                "intel" if "intel" in low else "other"
            name = re.sub(r"Corporation|\[AMD/ATI\]|Advanced Micro Devices, Inc\.", "", name)
            found.append({"vendor": vendor, "name": re.sub(r"\s+", " ", name).strip()})
    return found


def _ram():
    m = re.search(r"MemTotal:\s+(\d+)", read("/proc/meminfo"))
    return human(int(m.group(1)) * 1024) if m else "—"


def _uptime():
    try:
        sec = int(float(read("/proc/uptime", "0").split()[0]))
    except (ValueError, IndexError):
        return "—"
    d, h, m = sec // 86400, sec % 86400 // 3600, sec % 3600 // 60
    return (f"{d} д " if d else "") + (f"{h} ч " if h or d else "") + f"{m} мин"


def info():
    rel = os_release() if not DEV else {"PRETTY_NAME": "AstraMars OS 45", "VERSION_ID": "45"}
    disk = shutil.disk_usage(HOME if os.path.exists(HOME) else "/")
    g = gpus()
    return {
        "name": rel.get("PRETTY_NAME", "AstraMars OS"),
        "version": rel.get("VERSION_ID", ""),
        "kernel": platform.release() if not DEV else "7.2.15-300.fc45.x86_64",
        "plasma": _plasma_version(),
        "cpu": _cpu() if not DEV else "AMD Ryzen 7 7840HS",
        "gpu": ", ".join(x["name"] for x in g) or "—",
        "ram": _ram() if not DEV else "32 ГБ",
        "diskUsed": human(disk.used), "diskTotal": human(disk.total),
        "diskFree": human(disk.free), "diskPercent": round(disk.used / disk.total * 100) if disk.total else 0,
        "host": socket.gethostname(),
        "user": USER,
        "uptime": _uptime() if not DEV else "2 ч 14 мин",
        "variant": read("/usr/share/astramars/variant", "standard"),
    }


def _plasma_version():
    if DEV:
        return "6.8.2"
    code, out = sh(["plasmashell", "--version"], timeout=5)
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", out) if code == 0 else None
    return m.group(1) if m else "—"


# --- Обновления (те же службы, что и в Магазине) ------------------------------

def update_status():
    if DEV:
        return {"phase": "idle", "available": {"version": "45.20261108"}, "booted": {"version": "45.20261101"},
                "staged": None, "checked_at": "2026-11-08T10:00:00+00:00"}
    try:
        with open(UPDATE_STATUS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def update_check():
    sh(["systemctl", "start", "--no-block", "astramars-update-check.service"])


def update_apply():
    sh(["systemctl", "start", "--no-block", "astramars-update-apply.service"])


def reboot():
    spawn("systemctl", "reboot")


def rollback():
    return helper("rollback")


# --- «Машина времени»: снимки домашних папок ----------------------------------

def snapshots_available():
    if DEV:
        return True, ""
    try:
        st = os.stat("/var/home")
    except OSError:
        return False, "нет папки /var/home"
    code, out = sh(["stat", "-f", "-c", "%T", "/var/home"])
    if out.strip() != "btrfs":
        return False, "домашние папки не на btrfs"
    if st.st_ino != 256:   # корень тома btrfs всегда имеет номер 256
        return False, "домашние папки не на отдельном томе btrfs"
    return True, ""


def snapshots():
    if DEV:
        return [{"name": "2026-11-08_09-00-00_auto", "date": "8 ноября, 09:00", "auto": True},
                {"name": "2026-11-07_21-14-02", "date": "7 ноября, 21:14", "auto": False},
                {"name": "2026-11-07_09-00-00_auto", "date": "7 ноября, 09:00", "auto": True}]
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября",
              "октября", "ноября", "декабря"]
    result = []
    try:
        names = sorted(os.listdir(SNAP_ROOT), reverse=True)
    except OSError:
        names = []
    for name in names:
        m = re.fullmatch(r"(\d{4})-(\d\d)-(\d\d)_(\d\d)-(\d\d)-\d\d(_auto)?", name)
        if m:
            date = f"{int(m.group(3))} {months[int(m.group(2)) - 1]} {m.group(1)}, {m.group(4)}:{m.group(5)}"
            result.append({"name": name, "date": date, "auto": bool(m.group(6))})
    return result


def snapshot_timer_enabled():
    if DEV:
        return True
    code, out = sh(["systemctl", "is-enabled", "astramars-snapshot.timer"])
    return out.strip() == "enabled"


def open_snapshot(name):
    path = os.path.join(SNAP_ROOT, name, os.path.basename(HOME))
    spawn("dolphin", "--new-window", path if os.path.isdir(path) else os.path.join(SNAP_ROOT, name))


def open_kde_settings(module=""):
    spawn("systemsettings", *([module] if module else []))
