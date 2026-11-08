"""Программы для Windows (.exe и .msi) через Bottles — двойным щелчком, без настройки.

Bottles ставится из Flathub при первом запуске .exe. Для всех программ одна «бутылка»
AstraMars (среда «Приложения»). Программы, которые точно не заработают, мы называем честно
и предлагаем замену.
"""

import os
import re

from .util import DEV, sh, spawn

BOTTLES = "com.usebottles.bottles"
BOTTLE = "AstraMars"

# (шаблон имени файла, почему не заработает, чем заменить: [(название, id во Flathub)])
KNOWN = [
    (r"valorant|riot|vanguard|faceit|esea|fortnite|pubg|warzone|battleye|easyanticheat|genshin|"
     r"league.?of.?legends|rainbow.?six|apex",
     "В игре защита от читов, которая не работает вне Windows.",
     [("Steam", "com.valvesoftware.Steam"), ("PortProton", "ru.linux_gaming.PortProton")]),
    (r"photoshop|lightroom|illustrator|premiere|after.?effects|creative.?cloud|adobe",
     "Программы Adobe в Linux почти не работают.",
     [("GIMP", "org.gimp.GIMP"), ("Krita", "org.kde.krita"), ("Kdenlive", "org.kde.kdenlive"),
      ("Inkscape", "org.inkscape.Inkscape")]),
    (r"officesetup|ms.?office|winword|excel|powerpoint|outlook|o365|microsoft.?365",
     "Современный Microsoft Office в Linux не работает.",
     [("ONLYOFFICE", "org.onlyoffice.desktopeditors"), ("LibreOffice", "org.libreoffice.LibreOffice")]),
    (r"kaspersky|avast|\beset|drweb|nod32|antivirus|\bavg",
     "Антивирусы для Windows в Linux не нужны и не работают.", []),
    (r"driver|nvidia|amd.?software|radeon|realtek|intel.?graphics|chipset",
     "Драйверы для Windows не нужны: AstraMars ставит свои драйверы сама.", []),
    (r"steamsetup|steam_?installer",
     "Steam есть в версии для Linux — лучше поставить её.", [("Steam", "com.valvesoftware.Steam")]),
    (r"discordsetup|telegram.?setup|tsetup|chromesetup|firefox.?setup|zoominstaller|spotifysetup",
     "У этой программы есть версия для Linux — она работает лучше.", []),
    (r"1cv8|1c.?enterprise|setup1c",
     "У 1С есть своя версия для Linux — скачайте её с сайта 1С.", []),
]
NATIVE = {
    "discord": ("Discord", "com.discordapp.Discord"), "telegram": ("Telegram", "org.telegram.desktop"),
    "tsetup": ("Telegram", "org.telegram.desktop"), "chrome": ("Google Chrome", "com.google.Chrome"),
    "firefox": ("Firefox", "org.mozilla.firefox"), "zoom": ("Zoom", "us.zoom.Zoom"),
    "spotify": ("Spotify", "com.spotify.Client"), "obs": ("OBS Studio", "com.obsproject.Studio"),
    "vlc": ("VLC", "org.videolan.VLC"), "yandex": ("Яндекс Браузер", "ru.yandex.Browser"),
}


def verdict(path):
    """{ok, reason, alternatives} — заработает ли программа, по имени файла."""
    name = os.path.basename(path).lower()
    for pattern, reason, alts in KNOWN:
        if re.search(pattern, name):
            extra = [v for k, v in NATIVE.items() if k in name]
            alts = alts or extra
            return {"ok": False, "reason": reason, "alternatives": [{"name": n, "id": i} for n, i in alts]}
    return {"ok": True, "reason": "", "alternatives": []}


def bottles_installed():
    if DEV:
        return os.environ.get("ASTRAMARS_SETTINGS_BOTTLES", "1") == "1"
    code, _ = sh(["flatpak", "info", BOTTLES])
    return code == 0


def _cli(*args, timeout=900):
    return sh(["flatpak", "run", "--command=bottles-cli", BOTTLES, *args], timeout=timeout)


def prepare(path, on_step):
    """Доступ к файлу, своя «бутылка». on_step(текст)."""
    if DEV:
        on_step("Готовлю среду Windows…")
        return
    folder = os.path.dirname(os.path.abspath(path))
    home = os.path.expanduser("~")
    target = "home" if folder.startswith(home + os.sep) or folder == home else folder
    sh(["flatpak", "override", "--user", f"--filesystem={target}", BOTTLES])
    code, out = _cli("list", "bottles", timeout=120)
    if BOTTLE not in out:
        on_step("Готовлю среду Windows (первый раз — несколько минут)…")
        code, out = _cli("new", "--bottle-name", BOTTLE, "--environment", "application", timeout=1800)
        if code != 0:
            raise RuntimeError("Bottles не смог создать среду: " + (out.splitlines()[-1] if out else "ошибка"))


def run(path):
    if DEV:
        print("run exe:", path)
        return
    spawn("flatpak", "run", "--command=bottles-cli", BOTTLES, "run", "-b", BOTTLE, "-e", os.path.abspath(path))


def open_bottles():
    spawn("flatpak", "run", BOTTLES)
