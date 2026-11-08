"""Готовые сценарии и хранение своих.

Сценарий — это несколько шагов, каждый шаг — команда bash.
  root: True      — шаг выполняется от администратора (pkexec, система спросит пароль)
  optional: True  — ошибка шага не останавливает сценарий
  show: True      — вывод шага показывается в результате
"""

import json
import os
import uuid

DOCS = '"$(xdg-user-dir DOCUMENTS 2>/dev/null || echo "$HOME")"'

BUILTIN = [
    {
        "id": "clean",
        "title": "Очистить систему",
        "subtitle": "Ненужные среды Flatpak, кэш миниатюр, старые журналы",
        "icon": "broom",
        "measureSpace": True,
        "steps": [
            {"title": "Удаляю ненужные среды Flatpak",
             "run": "flatpak uninstall --unused -y --noninteractive; flatpak uninstall --user --unused -y --noninteractive",
             "optional": True},
            {"title": "Очищаю кэш миниатюр", "run": 'rm -rf "$HOME/.cache/thumbnails/"*'},
            {"title": "Удаляю журналы старше двух недель", "run": "journalctl --vacuum-time=14d", "root": True,
             "optional": True},
        ],
    },
    {
        "id": "update",
        "title": "Обновить всё",
        "subtitle": "Все приложения сейчас, систему — в фоне до перезагрузки",
        "icon": "refresh",
        "steps": [
            {"title": "Обновляю приложения", "run": "flatpak update -y --noninteractive"},
            {"title": "Запускаю скачивание новой версии системы",
             "run": "systemctl start --no-block astramars-update-apply.service && "
                    "echo 'Система скачивается в фоне. Новая версия включится после перезагрузки.'",
             "show": True},
        ],
    },
    {
        "id": "audio",
        "title": "Починить звук",
        "subtitle": "Перезапуск звуковой системы PipeWire",
        "icon": "volume",
        "steps": [
            {"title": "Перезапускаю PipeWire", "run": "systemctl --user restart wireplumber pipewire pipewire-pulse"},
            {"title": "Проверяю устройства вывода",
             "run": "sleep 1; wpctl status | sed -n '/Sinks:/,/Sources:/p' | grep -v Sources:", "show": True,
             "optional": True},
        ],
    },
    {
        "id": "network",
        "title": "Перезапустить сеть",
        "subtitle": "Выключить и включить Wi-Fi и проводную сеть",
        "icon": "wifi",
        "steps": [
            {"title": "Выключаю сеть", "run": "nmcli networking off"},
            {"title": "Включаю сеть", "run": "sleep 2; nmcli networking on"},
            {"title": "Жду подключения", "run": "nm-online -t 30 >/dev/null && nmcli -t -f NAME,TYPE connection show --active",
             "show": True},
        ],
    },
    {
        "id": "internet",
        "title": "Проверить интернет",
        "subtitle": "Задержка, DNS и скорость скачивания",
        "icon": "gauge",
        "steps": [
            {"title": "Задержка до 1.1.1.1",
             "run": "ping -c 4 -W 2 1.1.1.1 | tail -1 | awk -F/ '{printf \"Задержка: %.0f мс\\n\", $5}'",
             "show": True},
            {"title": "Проверяю DNS", "run": "getent hosts flathub.org >/dev/null && echo 'DNS: работает'",
             "show": True},
            {"title": "Скорость скачивания",
             "run": "curl -s -o /dev/null --max-time 20 -w '%{speed_download}' "
                    "'https://speed.cloudflare.com/__down?bytes=25000000' "
                    "| awk '{printf \"Скорость: %.1f Мбит/с\\n\", $1*8/1000000}'",
             "show": True, "optional": True},
        ],
    },
    {
        "id": "dns",
        "title": "Очистить кэш DNS",
        "subtitle": "Если сайты не открываются после смены сети или VPN",
        "icon": "globe",
        "steps": [
            {"title": "Очищаю кэш DNS", "run": "resolvectl flush-caches && echo 'Кэш DNS очищен'", "root": True,
             "show": True},
        ],
    },
    {
        "id": "desktop",
        "title": "Перезапустить рабочий стол",
        "subtitle": "Если зависла панель или меню. Окна не закроются",
        "icon": "monitor",
        "steps": [
            {"title": "Перезапускаю панель и рабочий стол",
             "run": "systemctl --user restart plasma-plasmashell.service"},
        ],
    },
    {
        "id": "space",
        "title": "Где место на диске",
        "subtitle": "Свободное место и самые большие папки",
        "icon": "pie",
        "steps": [
            {"title": "Свободное место",
             "run": "df -h --output=size,used,avail,pcent \"$HOME\" | tail -1 "
                    "| awk '{printf \"Диск: %s, занято %s (%s), свободно %s\\n\", $1, $2, $4, $3}'",
             "show": True},
            {"title": "Самые большие папки",
             "run": "du -sh \"$HOME\"/* \"$HOME/.cache\" \"$HOME/.local/share/flatpak\" /var/lib/flatpak "
                    "2>/dev/null | sort -rh | head -8",
             "show": True, "optional": True},
        ],
    },
    {
        "id": "backup",
        "title": "Копия настроек",
        "subtitle": "Настройки программ и рабочего стола — в архив в «Документах»",
        "icon": "archive",
        "steps": [
            {"title": "Упаковываю настройки",
             "run": f'f={DOCS}/astramars-настройки-$(date +%Y-%m-%d_%H-%M).tar.gz; '
                    'tar -czf "$f" -C "$HOME" --exclude=.config/*/Cache* --exclude=.config/*/cache* '
                    '.config .local/share/plasma .local/share/konsole 2>/dev/null; '
                    'echo "Сохранено: $f ($(du -h "$f" | cut -f1))"',
             "show": True},
        ],
    },
    {
        "id": "trash",
        "title": "Очистить корзину",
        "subtitle": "Удалить файлы из корзины навсегда",
        "icon": "trash",
        "confirm": "Файлы из корзины удалятся навсегда. Продолжить?",
        "measureSpace": True,
        "steps": [
            {"title": "Очищаю корзину",
             "run": 'rm -rf "$HOME/.local/share/Trash/files/"* "$HOME/.local/share/Trash/info/"* '
                    '"$HOME/.local/share/Trash/expunged/"*'},
        ],
    },
    {
        "id": "bluetooth",
        "title": "Перезапустить Bluetooth",
        "subtitle": "Если наушники или мышь не подключаются",
        "icon": "bluetooth",
        "steps": [
            {"title": "Перезапускаю Bluetooth", "run": "systemctl restart bluetooth && echo 'Bluetooth перезапущен'",
             "root": True, "show": True},
        ],
    },
    {
        "id": "sysinfo",
        "title": "Сведения о системе",
        "subtitle": "Процессор, видеокарта, память — чтобы отправить в поддержку",
        "icon": "info",
        "steps": [
            {"title": "Собираю сведения", "run": "fastfetch --logo none --pipe 2>/dev/null || uname -a", "show": True},
        ],
    },
]


def _path():
    base = os.environ.get("ASTRAMARS_ACTIONS_HOME") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "astramars-actions")
    return os.path.join(base, "actions.json")


def load_custom():
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
        return [a for a in data.get("custom", []) if a.get("id") and a.get("steps")]
    except (OSError, ValueError):
        return []


def save_custom(custom):
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"custom": custom}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def make_custom(title, commands, root, action_id=None):
    """Свой сценарий: каждая непустая строка (кроме # комментариев) — отдельный шаг."""
    lines = [l.rstrip() for l in commands.splitlines()]
    steps = [{"title": l.strip()[:80], "run": l.strip(), "root": bool(root), "show": True}
             for l in lines if l.strip() and not l.strip().startswith("#")]
    return {
        "id": action_id or "custom-" + uuid.uuid4().hex[:8],
        "title": title.strip() or "Моё действие",
        "subtitle": f"{len(steps)} {'команда' if len(steps) == 1 else 'команды' if 2 <= len(steps) <= 4 else 'команд'}"
                    + (" · от администратора" if root else ""),
        "icon": "terminal",
        "custom": True,
        "root": bool(root),
        "commands": "\n".join(lines).strip(),
        "steps": steps,
    }
