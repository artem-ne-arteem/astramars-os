"""Переезд с Windows: найти диск Windows, перенести папки, закладки браузеров и обои.

Диск Windows подключается только для чтения — с ним ничего не случится.
Пароли браузеров перенести нельзя: Windows шифрует их ключом своей учётной записи.
"""

import glob
import html
import json
import os
import re
import shutil
import sqlite3
import tempfile
import time

from .util import DEV, HOME, human, sh, spawn, xdg_dir

SKIP_USERS = {"public", "default", "default user", "all users", "defaultapppool", "wdagutilityaccount"}
FOLDERS = [
    # id, папка Windows, папка XDG, запасное имя, подпись
    ("desktop", "Desktop", "DESKTOP", "Desktop", "Рабочий стол"),
    ("documents", "Documents", "DOCUMENTS", "Documents", "Документы"),
    ("pictures", "Pictures", "PICTURES", "Pictures", "Изображения"),
    ("music", "Music", "MUSIC", "Music", "Музыка"),
    ("videos", "Videos", "VIDEOS", "Videos", "Видео"),
    ("downloads", "Downloads", "DOWNLOAD", "Downloads", "Загрузки"),
]
SUBDIR = "Из Windows"
CHROMIUM = [
    ("Google Chrome", "AppData/Local/Google/Chrome/User Data"),
    ("Microsoft Edge", "AppData/Local/Microsoft/Edge/User Data"),
    ("Яндекс Браузер", "AppData/Local/Yandex/YandexBrowser/User Data"),
    ("Brave", "AppData/Local/BraveSoftware/Brave-Browser/User Data"),
    ("Opera", "AppData/Roaming/Opera Software/Opera Stable"),
    ("Opera GX", "AppData/Roaming/Opera Software/Opera GX Stable"),
]
FIREFOX = "AppData/Roaming/Mozilla/Firefox/Profiles"
FIREFOX_ROOTS = {"menu": "Меню закладок", "toolbar": "Панель закладок", "unfiled": "Другие закладки",
                 "mobile": "С телефона"}
WALLPAPER = "AppData/Roaming/Microsoft/Windows/Themes/TranscodedWallpaper"


class WinError(Exception):
    pass


# --- Поиск диска Windows ------------------------------------------------------------

def partitions():
    """NTFS-разделы: [{path, label, size, mount, uuid}]."""
    if DEV:
        return [{"path": "/dev/nvme0n1p3", "label": "Windows", "size": "412 ГБ",
                 "mount": os.path.join(HOME, "fake-windows"), "uuid": "1234ABCD"}]
    code, out = sh(["lsblk", "-J", "-b", "-o", "PATH,FSTYPE,LABEL,SIZE,MOUNTPOINTS,UUID"])
    if code != 0:
        return []
    found = []

    def walk(devs):
        for d in devs:
            if (d.get("fstype") or "").lower() == "ntfs" and int(d.get("size") or 0) > 20 * 1024 ** 3:
                mounts = [m for m in (d.get("mountpoints") or []) if m]
                found.append({"path": d["path"], "label": d.get("label") or "", "size": human(d.get("size")),
                              "mount": mounts[0] if mounts else "", "uuid": d.get("uuid") or ""})
            walk(d.get("children") or [])
    walk(json.loads(out).get("blockdevices", []))
    return found


def mount(part):
    """Подключает раздел только для чтения, возвращает папку."""
    if part.get("mount"):
        return part["mount"]
    code, out = sh(["udisksctl", "mount", "--no-user-interaction", "-b", part["path"], "-o", "ro"], timeout=60)
    m = re.search(r" at (/\S.*?)\.?$", out.strip())
    if code == 0 and m:
        return m.group(1)
    low = out.lower()
    if "hibernat" in low or "unclean" in low or "dirty" in low or "fast startup" in low:
        raise WinError("Windows не завершила работу до конца (включён «Быстрый запуск» или гибернация). "
                       "Загрузите Windows и выберите «Пуск → Выключение» с зажатой клавишей Shift — "
                       "или отключите «Быстрый запуск» в Панели управления → Электропитание.")
    if "bitlocker" in low or "encrypted" in low:
        raise WinError("Диск Windows зашифрован BitLocker — сначала отключите шифрование в Windows.")
    raise WinError("Не удалось подключить диск Windows: " + (out.splitlines()[-1] if out else "ошибка"))


def find_windows():
    """[{part, root, users: [{name, path}]}] — разделы, где установлена Windows."""
    result, errors = [], []
    for part in partitions():
        try:
            root = mount(part)
        except WinError as e:
            errors.append(str(e))
            continue
        users_dir = os.path.join(root, "Users")
        if not os.path.isdir(users_dir):
            continue
        users = []
        for name in sorted(os.listdir(users_dir)):
            path = os.path.join(users_dir, name)
            if name.lower() in SKIP_USERS or not os.path.isdir(path) or os.path.islink(path):
                continue
            if os.path.isdir(os.path.join(path, "Desktop")) or os.path.isdir(os.path.join(path, "Documents")):
                users.append({"name": name, "path": path})
        if users:
            result.append({"device": part["path"], "label": part["label"] or "Windows", "size": part["size"],
                           "root": root, "uuid": part["uuid"], "users": users})
    return result, errors


# --- Перенос ------------------------------------------------------------------------

def _files(src):
    for dirpath, dirnames, filenames in os.walk(src, onerror=lambda e: None):
        # Ярлыки и служебные файлы Windows не нужны
        dirnames[:] = [d for d in dirnames if d not in ("$RECYCLE.BIN", "desktop.ini") and not
                       os.path.islink(os.path.join(dirpath, d))]
        for f in filenames:
            if f.lower() in ("desktop.ini", "thumbs.db") or f.lower().endswith(".lnk"):
                continue
            yield os.path.join(dirpath, f)


def plan(user_path, folder_ids):
    """Сколько файлов и байт придётся скопировать."""
    count, total = 0, 0
    for fid, win, *_ in FOLDERS:
        if fid in folder_ids:
            for path in _files(os.path.join(user_path, win)):
                try:
                    total += os.path.getsize(path)
                    count += 1
                except OSError:
                    pass
    return count, total


def copy_folders(user_path, folder_ids, on_progress, cancelled=lambda: False):
    """Копирует выбранные папки в «<папка>/Из Windows». on_progress(процент, текст)."""
    count, total = plan(user_path, folder_ids)
    free = shutil.disk_usage(HOME).free
    if total > free - 2 * 1024 ** 3:
        raise WinError(f"Не хватит места: нужно {human(total)}, свободно {human(free)}")
    done, copied, failed = 0, 0, 0
    last = 0.0
    for fid, win, kind, fallback, title in FOLDERS:
        if fid not in folder_ids:
            continue
        src = os.path.join(user_path, win)
        dst_root = os.path.join(xdg_dir(kind, fallback), SUBDIR)
        for path in _files(src):
            if cancelled():
                return copied, failed, "отменено"
            rel = os.path.relpath(path, src)
            dst = os.path.join(dst_root, rel)
            try:
                size = os.path.getsize(path)
                if not (os.path.exists(dst) and os.path.getsize(dst) == size):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(path, dst)
                copied += 1
                done += size
            except OSError:
                failed += 1     # файлы OneDrive «только в облаке», занятые и повреждённые
            if time.monotonic() - last > 0.2:
                last = time.monotonic()
                pct = int(done / total * 100) if total else 100
                on_progress(pct, f"{title}: {human(done)} из {human(total)}")
    on_progress(100, f"Скопировано {copied} файлов, {human(done)}")
    return copied, failed, ""


# --- Закладки -------------------------------------------------------------------------

def _chromium_nodes(node, out):
    if node.get("type") == "url" and node.get("url", "").startswith(("http://", "https://")):
        out.append(("link", node.get("name") or node["url"], node["url"]))
    elif node.get("type") == "folder" or "children" in node:
        children = []
        for child in node.get("children", []):
            _chromium_nodes(child, children)
        if children:
            out.append(("folder", node.get("name") or "Папка", children))


def _chromium(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for root in (data.get("roots") or {}).values():
        if isinstance(root, dict):
            _chromium_nodes(root, items)
    return items


def _firefox(places):
    tmp = tempfile.mkdtemp()
    try:
        copy = os.path.join(tmp, "places.sqlite")
        shutil.copy2(places, copy)
        con = sqlite3.connect(copy)
        rows = con.execute("SELECT b.id, b.parent, b.type, b.title, p.url FROM moz_bookmarks b "
                           "LEFT JOIN moz_places p ON p.id = b.fk ORDER BY b.parent, b.position").fetchall()
        con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    by_parent = {}
    for row in rows:
        by_parent.setdefault(row[1], []).append(row)

    def build(parent, depth=0):
        out = []
        for bid, _, typ, title, url in by_parent.get(parent, []):
            if typ == 1 and url and url.startswith(("http://", "https://")):
                out.append(("link", title or url, url))
            elif typ == 2 and depth < 20:
                children = build(bid, depth + 1)
                if children:
                    title = FIREFOX_ROOTS.get(title, title) if depth == 0 else title
                    out.append(("folder", title or "Папка", children))
        return out
    return build(1)   # 1 — корень закладок Firefox


def collect_bookmarks(user_path):
    """[(браузер, дерево)] — закладки всех найденных браузеров."""
    found = []
    for name, base in CHROMIUM:
        for path in sorted(glob.glob(os.path.join(user_path, base, "*", "Bookmarks")) +
                           glob.glob(os.path.join(user_path, base, "Bookmarks"))):
            try:
                tree = _chromium(path)
            except (OSError, ValueError):
                continue
            if tree:
                profile = os.path.basename(os.path.dirname(path))
                found.append((name if profile in ("Default", os.path.basename(base)) else f"{name} ({profile})",
                              tree))
    for places in glob.glob(os.path.join(user_path, FIREFOX, "*", "places.sqlite")):
        try:
            tree = _firefox(places)
        except (OSError, sqlite3.Error):
            continue
        if tree:
            found.append(("Firefox", tree))
    return found


def _html(items, indent=1):
    pad = "    " * indent
    out = []
    for kind, title, value in items:
        if kind == "link":
            out.append(f'{pad}<DT><A HREF="{html.escape(value, True)}">{html.escape(title)}</A>')
        else:
            out.append(f"{pad}<DT><H3>{html.escape(title)}</H3>\n{pad}<DL><p>")
            out.append(_html(value, indent + 1))
            out.append(f"{pad}</DL><p>")
    return "\n".join(out)


def export_bookmarks(user_path):
    """Файл закладок в формате, который понимают все браузеры («Импорт из HTML»)."""
    browsers = collect_bookmarks(user_path)
    if not browsers:
        return "", 0
    count = 0

    def links(items):
        return sum(1 if k == "link" else links(v) for k, _, v in items)
    body = []
    for name, tree in browsers:
        count += links(tree)
        body.append(("folder", f"{name} (из Windows)", tree))
    text = ("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n'
            "<TITLE>Bookmarks</TITLE>\n<H1>Закладки из Windows</H1>\n<DL><p>\n" + _html(body) + "\n</DL><p>\n")
    dst_dir = os.path.join(xdg_dir("DOCUMENTS", "Documents"), SUBDIR)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, "Закладки из Windows.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    return dst, count


# --- Обои ---------------------------------------------------------------------------------

def import_wallpaper(user_path):
    src = os.path.join(user_path, WALLPAPER)
    if not os.path.isfile(src):
        return ""
    dst_dir = os.path.join(HOME, ".local", "share", "wallpapers")
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, "windows-wallpaper.jpg")
    shutil.copy2(src, dst)
    if not DEV:
        sh(["plasma-apply-wallpaperimage", dst])
    return dst


# --- Диск Windows в «Файлах» при каждом входе ----------------------------------------

AUTOSTART = os.path.join(HOME, ".config", "autostart", "astramars-windows-disk.desktop")


def automount_enabled():
    return os.path.exists(AUTOSTART)


def set_automount(uuid, on):
    if not on:
        if os.path.exists(AUTOSTART):
            os.remove(AUTOSTART)
        return True
    if not re.fullmatch(r"[0-9A-Fa-f-]+", uuid or ""):
        return False
    os.makedirs(os.path.dirname(AUTOSTART), exist_ok=True)
    with open(AUTOSTART, "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\nType=Application\nName=Диск Windows\nNoDisplay=true\n"
                "Comment=AstraMars: подключить диск Windows только для чтения\n"
                f"Exec=udisksctl mount --no-user-interaction -b /dev/disk/by-uuid/{uuid} -o ro\n"
                "X-KDE-autostart-phase=2\n")
    return True


def open_folder(path):
    spawn("dolphin", "--new-window", path)
