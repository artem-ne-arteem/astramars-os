"""Хранение серверов, подписок и настроек в ~/.config/astramars-vpn/state.json."""

import json
import os
import secrets

DEFAULTS = {
    "servers": [],
    "subscriptions": [],
    "selected": "",
    "mode": "tun",
    "bypass_ru": True,
    "autoconnect": False,
    "api_secret": "",
}


def config_dir() -> str:
    return os.environ.get("ASTRAMARS_VPN_HOME") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "astramars-vpn")


def _path() -> str:
    return os.path.join(config_dir(), "state.json")


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        with open(_path(), encoding="utf-8") as f:
            data.update(json.load(f))
    except (OSError, ValueError):
        pass
    if not data["api_secret"]:
        data["api_secret"] = secrets.token_hex(16)
    return data


def save(data: dict) -> None:
    write_private(_path(), json.dumps(data, ensure_ascii=False, indent=2))


def write_private(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)
