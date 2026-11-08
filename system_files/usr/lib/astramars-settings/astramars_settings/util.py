"""Общие мелочи: запуск команд, помощник администратора, файлы настроек."""

import json
import os
import shutil
import subprocess

DEV = bool(os.environ.get("ASTRAMARS_SETTINGS_DEV"))
HOME = os.environ.get("ASTRAMARS_SETTINGS_HOME") or os.path.expanduser("~")
HELPER = "/usr/libexec/astramars-settings-helper"
USER = os.environ.get("USER") or os.environ.get("USERNAME") or "user"


def sh(args, timeout=30, env=None):
    """(код, вывод) — без исключений: нет программы → код 127."""
    if isinstance(args, str):
        args = ["bash", "-c", args]
    if not shutil.which(args[0]) and not os.path.exists(args[0]):
        return 127, f"{args[0]}: не найдено"
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, **(env or {})), stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return 124, "превышено время ожидания"
    except OSError as e:
        return 126, str(e)
    return p.returncode, (p.stdout + ("\n" + p.stderr if p.returncode and p.stderr else "")).strip()


def helper(*args, timeout=600):
    """Действие от администратора через pkexec. (успех, текст)."""
    if DEV:
        return True, "ok"
    code, out = sh(["pkexec", HELPER, *args], timeout=timeout)
    if code in (126, 127) and "pkexec" in out:
        return False, "нет прав администратора"
    last = out.strip().splitlines()[-1] if out.strip() else ""
    return code == 0, last


def spawn(*args):
    """Запустить программу отдельно от нас (окно, браузер, Dolphin)."""
    if DEV:
        print("spawn:", args)
        return
    try:
        subprocess.Popen(list(args), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def config_path(name):
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
    return os.path.join(base, "astramars", name)


def load_json(name, default=None):
    try:
        with open(config_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default if default is not None else {}


def save_json(name, data, private=False):
    path = config_path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    if private:
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return default


def human(n):
    n = float(n or 0)
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024 or unit == "ТБ":
            return (f"{n:.0f} {unit}" if unit in ("Б", "КБ") or n >= 100 else f"{n:.1f} {unit}").replace(".", ",")
        n /= 1024
    return ""


def xdg_dir(kind, fallback):
    """Папка пользователя (Документы, Изображения…) — с учётом языка системы."""
    if not DEV:
        code, out = sh(["xdg-user-dir", kind])
        if code == 0 and out and out != HOME:
            return out
    return os.path.join(HOME, fallback)
