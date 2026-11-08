"""Игры: набор программ одной кнопкой, MangoHud, игровой режим, образ с драйверами NVIDIA."""

import json
import re

from . import power
from .system import gpus
from .util import DEV, helper, read, sh

KIT = [
    {"id": "com.valvesoftware.Steam", "name": "Steam", "hint": "Магазин и Proton для игр с Windows"},
    {"id": "com.heroicgameslauncher.hgl", "name": "Heroic", "hint": "Epic Games, GOG и Amazon"},
    {"id": "ru.linux_gaming.PortProton", "name": "PortProton", "hint": "Игры и лаунчеры не из Steam"},
    {"id": "net.davidotek.pupgui2", "name": "ProtonUp-Qt", "hint": "Новые версии Proton"},
]
MANGOHUD = "org.freedesktop.Platform.VulkanLayer.MangoHud"
STEAM = "com.valvesoftware.Steam"


def variant():
    return read("/usr/share/astramars/variant", "standard") if not DEV else "standard"


def nvidia_present():
    return any(g["vendor"] == "nvidia" for g in gpus())


def steam_runtime_branch():
    """Ветка среды Steam (например 24.08) — MangoHud ставится в ту же."""
    code, out = sh(["flatpak", "info", "--show-runtime", STEAM])
    m = re.search(r"/(\d+\.\d+)$", out.strip()) if code == 0 else None
    return m.group(1) if m else ""


def mangohud_ref():
    branch = steam_runtime_branch()
    return f"runtime/{MANGOHUD}/x86_64/{branch}" if branch else ""


def mangohud_enabled():
    if DEV:
        return False
    code, out = sh(["flatpak", "override", "--user", "--show", STEAM])
    return "MANGOHUD=1" in out


def set_mangohud(on):
    if DEV:
        return True
    args = ["--env=MANGOHUD=1"] if on else ["--unset-env=MANGOHUD"]
    code, _ = sh(["flatpak", "override", "--user", *args, STEAM])
    return code == 0


def game_mode():
    return power.profile() == "performance"


def set_game_mode(on):
    return power.set_profile("performance" if on else "balanced")


def gamemode_available():
    return DEV or sh(["bash", "-c", "command -v gamemoded"])[0] == 0


def switch_image(kind):
    return helper("image", kind, timeout=60)


def switch_status():
    """{state: idle|running|failed, staged: standard|nvidia|""} — переход на другой образ идёт в фоне."""
    if DEV:
        return {"state": "idle", "staged": ""}
    code, out = sh(["systemctl", "show", "-p", "ActiveState", "astramars-image-switch.service"])
    active = out.strip().split("=", 1)[-1]
    state = "running" if active in ("active", "activating") else "failed" if active == "failed" else "idle"
    staged = ""
    code, out = sh(["rpm-ostree", "status", "--json"], timeout=30)
    try:
        for dep in json.loads(out).get("deployments", []) if code == 0 else []:
            if dep.get("staged"):
                ref = json.dumps(dep.get("container-image-reference") or dep.get("origin") or "")
                staged = "nvidia" if "astramars-os-nvidia" in ref else "standard"
    except ValueError:
        pass
    return {"state": state, "staged": staged}


def secure_boot():
    if DEV:
        return True
    code, out = sh(["mokutil", "--sb-state"])
    return "enabled" in out.lower()


def mok_enroll():
    return helper("mok-enroll", timeout=60)
