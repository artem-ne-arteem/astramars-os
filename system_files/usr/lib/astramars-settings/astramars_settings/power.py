"""Ноутбук: заряд и здоровье батареи, профили питания, яркость, предел заряда."""

import glob
import os
import re

from .util import DEV, helper, read, sh

PROFILES = [
    {"id": "power-saver", "name": "Тихо", "hint": "Дольше от батареи"},
    {"id": "balanced", "name": "Баланс", "hint": "Обычная работа"},
    {"id": "performance", "name": "Мощно", "hint": "Игры и тяжёлые задачи"},
]


def batteries():
    if DEV:
        return [{"name": "BAT0", "percent": 76, "status": "Разряжается", "health": 91, "limit": 80,
                 "limitSupported": True, "time": "≈ 4 ч 10 мин"}]
    result = []
    for path in sorted(glob.glob("/sys/class/power_supply/*")):
        if read(os.path.join(path, "type")) != "Battery" or read(os.path.join(path, "scope")) == "Device":
            continue
        full = read(os.path.join(path, "energy_full")) or read(os.path.join(path, "charge_full"))
        design = read(os.path.join(path, "energy_full_design")) or read(os.path.join(path, "charge_full_design"))
        try:
            health = round(int(full) / int(design) * 100) if full and design and int(design) else 0
        except ValueError:
            health = 0
        status = read(os.path.join(path, "status"))
        limit_file = os.path.join(path, "charge_control_end_threshold")
        result.append({
            "name": os.path.basename(path),
            "percent": int(read(os.path.join(path, "capacity"), "0") or 0),
            "status": {"Charging": "Заряжается", "Discharging": "Разряжается", "Full": "Заряжена",
                       "Not charging": "Не заряжается"}.get(status, status),
            "health": min(health, 100),
            "limit": int(read(limit_file, "100") or 100) if os.path.exists(limit_file) else 100,
            "limitSupported": os.path.exists(limit_file),
            "time": _time_left(path, status),
        })
    return result


def _time_left(path, status):
    try:
        now = int(read(os.path.join(path, "energy_now")) or read(os.path.join(path, "charge_now")) or 0)
        rate = int(read(os.path.join(path, "power_now")) or read(os.path.join(path, "current_now")) or 0)
        full = int(read(os.path.join(path, "energy_full")) or read(os.path.join(path, "charge_full")) or 0)
    except ValueError:
        return ""
    if rate <= 0:
        return ""
    hours = now / rate if status == "Discharging" else (full - now) / rate if status == "Charging" else 0
    if hours <= 0 or hours > 30:
        return ""
    h, m = int(hours), int(hours * 60) % 60
    return f"≈ {h} ч {m} мин" if status == "Discharging" else f"до полной ≈ {h} ч {m} мин"


def set_charge_limit(value):
    return helper("charge-limit", str(int(value)), timeout=30)


def profile():
    if DEV:
        return "balanced"
    code, out = sh(["powerprofilesctl", "get"])
    return out.strip() if code == 0 else ""


def profiles_available():
    if DEV:
        return [p["id"] for p in PROFILES]
    code, out = sh(["powerprofilesctl", "list"])
    if code != 0:
        return []
    return [p["id"] for p in PROFILES if re.search(rf"^\s*\*?\s*{p['id']}:", out, re.M)]


def set_profile(pid):
    if DEV:
        return True
    code, _ = sh(["powerprofilesctl", "set", pid])
    return code == 0


def brightness():
    """Яркость экрана в процентах, или -1, если её нельзя менять (обычный монитор)."""
    if DEV:
        return 60
    code, out = sh(["brightnessctl", "-m", "-c", "backlight"])
    m = re.search(r",(\d+)%,", out) if code == 0 else None
    return int(m.group(1)) if m else -1


def set_brightness(pct):
    if DEV:
        return
    sh(["brightnessctl", "-q", "-c", "backlight", "set", f"{max(1, min(100, int(pct)))}%"])
