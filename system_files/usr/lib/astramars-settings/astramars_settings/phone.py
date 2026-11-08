"""Телефон рядом: KDE Connect — уведомления, файлы, общий буфер обмена и SMS с Android."""

import base64
import io
import re

from .util import DEV, sh, spawn

ANDROID_URL = "https://play.google.com/store/apps/details?id=org.kde.kdeconnect_tp"
FDROID_URL = "https://f-droid.org/packages/org.kde.kdeconnect_tp/"
IOS_URL = "https://apps.apple.com/app/kde-connect/id1580245991"
LINE = re.compile(r"^-\s+(.+?):\s+(\S+)\s+\((.+)\)\s*$")


def installed():
    return DEV or sh(["bash", "-c", "command -v kdeconnect-cli"])[0] == 0


def devices():
    """[{id, name, paired, reachable}]"""
    if DEV:
        return [{"id": "a1b2c3", "name": "Pixel 8", "paired": True, "reachable": True},
                {"id": "d4e5f6", "name": "Galaxy Tab S9", "paired": False, "reachable": True}]
    code, out = sh(["kdeconnect-cli", "-l"], timeout=15)
    result = []
    for line in out.splitlines() if code == 0 else []:
        m = LINE.match(line.strip())
        if m:
            state = m.group(3).lower()
            result.append({"id": m.group(2), "name": m.group(1), "reachable": "reachable" in state,
                           "paired": "paired" in state and "unpaired" not in state})
    return result


def _cli(*args):
    if DEV:
        return True, ""
    code, out = sh(["kdeconnect-cli", *args], timeout=20)
    return code == 0, out


def refresh():
    return _cli("--refresh")


def pair(dev):
    return _cli("--pair", "-d", dev)


def unpair(dev):
    return _cli("--unpair", "-d", dev)


def ring(dev):
    return _cli("--ring", "-d", dev)


def ping(dev):
    return _cli("--ping-msg", "Привет от AstraMars 🐾", "-d", dev)


def share(dev, path):
    return _cli("--share", path, "-d", dev)


def open_app():
    spawn("kdeconnect-app")


def open_settings():
    spawn("systemsettings", "kcm_kdeconnect")


def qr(url=ANDROID_URL):
    """QR-код ссылки на приложение — картинка data: для QML."""
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return ""
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathFillImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()
