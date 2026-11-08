"""Каталог: подборка по разделам и полный список приложений Flathub из данных AppStream.

AppStream — это файл со всеми приложениями репозитория (названия, описания на разных языках,
иконки). Flatpak скачивает его сам вместе с репозиторием, поэтому поиск работает без отдельных
запросов в интернет.
"""

import glob
import pathlib
import gzip
import os
import xml.etree.ElementTree as ET

# Подборка: раздел → приложения Flathub (порядок = порядок на экране)
CURATED = [
    ("internet", "Интернет", [
        "org.mozilla.firefox", "com.google.Chrome", "com.brave.Browser",
        "io.github.ungoogled_software.ungoogled_chromium", "org.qbittorrent.qBittorrent",
        "com.transmissionbt.Transmission",
    ]),
    ("chat", "Общение", [
        "org.telegram.desktop", "com.discordapp.Discord", "us.zoom.Zoom",
        "org.mozilla.thunderbird", "im.riot.Riot", "com.viber.Viber",
    ]),
    ("games", "Игры", [
        "com.valvesoftware.Steam", "com.heroicgameslauncher.hgl", "net.lutris.Lutris",
        "com.usebottles.bottles", "org.prismlauncher.PrismLauncher", "net.davidotek.pupgui2",
    ]),
    ("media", "Мультимедиа", [
        "org.videolan.VLC", "com.spotify.Client", "com.obsproject.Studio",
        "io.mpv.Mpv", "org.kde.elisa", "com.github.wwmm.easyeffects",
    ]),
    ("office", "Работа", [
        "org.libreoffice.LibreOffice", "org.onlyoffice.desktopeditors", "md.obsidian.Obsidian",
        "com.anydesk.Anydesk", "org.kde.okular", "com.github.xournalpp.xournalpp",
    ]),
    ("create", "Творчество", [
        "org.gimp.GIMP", "org.kde.krita", "org.blender.Blender",
        "org.kde.kdenlive", "org.audacityteam.Audacity", "org.inkscape.Inkscape",
    ]),
    ("dev", "Разработка", [
        "com.visualstudio.code", "com.jetbrains.PyCharm-Professional", "io.podman_desktop.PodmanDesktop",
        "io.github.shiftey.Desktop", "org.gnome.Boxes", "com.getpostman.Postman",
    ]),
    ("tools", "Утилиты", [
        "com.github.tchx84.Flatseal", "io.github.flattool.Warehouse", "org.localsend.localsend_app",
        "io.github.peazip.PeaZip", "org.kde.kcalc", "net.nokyan.Resources",
    ]),
]

FEATURED = ["org.telegram.desktop", "com.valvesoftware.Steam", "com.obsproject.Studio", "org.videolan.VLC"]

APP_TYPES = {"desktop-application", "desktop"}
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def appstream_dirs():
    """Папки с данными AppStream Flathub: заданная для тестов, системная, пользовательская."""
    if os.environ.get("ASTRAMARS_STORE_APPSTREAM"):
        return [os.environ["ASTRAMARS_STORE_APPSTREAM"]]
    roots = ["/var/lib/flatpak", os.path.expanduser("~/.local/share/flatpak")]
    found = []
    for root in roots:
        found += sorted(glob.glob(os.path.join(root, "appstream", "flathub", "*", "active")))
    return [d for d in found if os.path.exists(os.path.join(d, "appstream.xml.gz"))
            or os.path.exists(os.path.join(d, "appstream.xml"))]


def _localized(component, tag, lang):
    best, fallback = None, None
    for el in component.findall(tag):
        code = el.get(XML_LANG)
        text = (el.text or "").strip()
        if not text:
            continue
        if code is None and fallback is None:
            fallback = text
        elif code and (code == lang or code.split("_")[0] == lang):
            best = best or text
    return best or fallback or ""


def _icon(component, base):
    best, best_size = "", 0
    for el in component.findall("icon"):
        kind = el.get("type")
        name = (el.text or "").strip()
        if kind == "remote" and not best:
            best = name
        if kind != "cached" or not name:
            continue
        size = int(el.get("height") or el.get("width") or 64)
        for folder in (f"{size}x{size}", f"{size}x{size}@2"):
            path = os.path.join(base, "icons", folder, name)
            if os.path.exists(path) and size > best_size:
                best, best_size = pathlib.Path(path).as_uri(), size
    return best


def parse_appstream(directory, lang="ru"):
    """{id: {...}} для всех настольных приложений в папке AppStream."""
    path = os.path.join(directory, "appstream.xml.gz")
    opener = gzip.open if os.path.exists(path) else open
    if not os.path.exists(path):
        path = os.path.join(directory, "appstream.xml")
    apps = {}
    with opener(path, "rb") as f:
        for _, comp in ET.iterparse(f):
            if comp.tag != "component":
                continue
            if comp.get("type") in APP_TYPES:
                app_id = (comp.findtext("id") or "").strip()
                if app_id.endswith(".desktop"):
                    app_id = app_id[:-8]
                bundle = comp.find("bundle")
                if bundle is not None and bundle.get("type") == "flatpak" and bundle.text:
                    app_id = bundle.text.split("/")[1]
                if app_id:
                    apps[app_id] = {
                        "id": app_id,
                        "name": _localized(comp, "name", lang) or app_id,
                        "summary": _localized(comp, "summary", lang),
                        "icon": _icon(comp, directory),
                        "developer": (comp.findtext("developer_name")
                                      or comp.findtext("developer/name") or "").strip(),
                        "categories": [c.text for c in comp.findall("categories/category") if c.text],
                    }
            comp.clear()
    return apps


def load_catalog(lang="ru"):
    apps = {}
    for directory in appstream_dirs():
        try:
            apps.update(parse_appstream(directory, lang))
        except (OSError, ET.ParseError):
            continue
    return apps


def search(apps, query, limit=60):
    """Поиск по названию, id, описанию и разработчику; сначала совпадения в начале названия."""
    q = query.strip().lower()
    if not q:
        return []
    scored = []
    for app in apps.values():
        name = app["name"].lower()
        hay = " ".join((app["id"], app["summary"], app["developer"])).lower()
        if name.startswith(q):
            score = 0
        elif q in name:
            score = 1
        elif q in hay:
            score = 2
        else:
            continue
        scored.append((score, len(name), app["name"], app))
    scored.sort(key=lambda t: t[:3])
    return [t[3] for t in scored[:limit]]
