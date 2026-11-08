"""Оформление: акцентный цвет (во всей системе и в наших приложениях), тёмная/светлая тема,
обои по времени суток, точечные часы на рабочем столе."""

import os

from .util import DEV, load_json, save_json, sh, spawn

ACCENTS = [
    {"id": "mars", "name": "Марс", "color": "#ff3b30"},
    {"id": "astra", "name": "Астра", "color": "#a970ff"},
    {"id": "dune", "name": "Дюна", "color": "#ff9f0a"},
    {"id": "sea", "name": "Море", "color": "#0a84ff"},
    {"id": "mint", "name": "Мята", "color": "#30d158"},
    {"id": "sakura", "name": "Сакура", "color": "#ff6fae"},
    {"id": "graphite", "name": "Графит", "color": "#a1a1a6"},
]
DEFAULT = "#ff3b30"
SCHEMES = {"dark": "BreezeDark", "light": "BreezeLight"}


def accent():
    return load_json("theme.json").get("accent", DEFAULT)


def scheme():
    return load_json("theme.json").get("scheme", "dark")


def _save(**kw):
    data = load_json("theme.json")
    data.update(kw)
    save_json("theme.json", data)


def set_accent(color):
    if color not in [a["color"] for a in ACCENTS]:
        return False
    _save(accent=color)
    if not DEV:
        sh(["plasma-apply-colorscheme", "--accent-color", color], timeout=20)
    return True


def set_scheme(kind):
    if kind not in SCHEMES:
        return False
    _save(scheme=kind)
    if not DEV:
        sh(["plasma-apply-colorscheme", SCHEMES[kind]], timeout=20)
        # Смена схемы сбрасывает акцент — возвращаем выбранный
        sh(["plasma-apply-colorscheme", "--accent-color", accent()], timeout=20)
    return True


def daytime_enabled():
    if DEV:
        return load_json("theme.json").get("daytime", False)
    code, out = sh(["systemctl", "--user", "is-enabled", "astramars-wallpaper.timer"])
    return out.strip() == "enabled"


def set_daytime(on):
    _save(daytime=bool(on))
    if DEV:
        return
    if on:
        sh(["systemctl", "--user", "enable", "--now", "astramars-wallpaper.timer"])
        sh(["/usr/libexec/astramars-wallpaper", "--force"])
    else:
        sh(["systemctl", "--user", "disable", "--now", "astramars-wallpaper.timer"])
        sh(["plasma-apply-wallpaperimage", "/usr/share/wallpapers/AstraMarsDots"])


def add_clock_widget():
    """Точечные часы — на каждый рабочий стол, в правый верхний угол."""
    if DEV:
        return True
    script = """
desktops().forEach(function (d) {
    var has = d.widgets("org.astramars.dotclock").length > 0;
    if (!has) {
        var g = screenGeometry(d.screen);
        d.addWidget("org.astramars.dotclock", g.width - 520, 60, 460, 220);
    }
});
"""
    code, _ = sh(["gdbus", "call", "--session", "--dest", "org.kde.plasmashell", "--object-path",
                  "/PlasmaShell", "--method", "org.kde.PlasmaShell.evaluateScript", script])
    return code == 0


def open_wallpaper_settings():
    spawn("systemsettings", "kcm_wallpaper")
