"""ИИ-помощник AstraMars на Claude (Anthropic API).

Помощник отвечает по-русски и может предложить кнопку: запустить Быстрое действие,
открыть раздел настроек или найти программу в Магазине. Сам он ничего не выполняет —
действие запускается, только когда пользователь нажмёт кнопку.

Ключ API хранится в ~/.config/astramars/assistant.json (доступ только у владельца).
Без ключа работает простой офлайн-режим: подсказки по ключевым словам.
"""

import os
import sys

from . import network, power, system
from .util import DEV, load_json, save_json

HERE = os.path.dirname(os.path.abspath(__file__))
for extra in (os.path.join(HERE, "..", "vendor"), os.path.join(HERE, "..", "..", "astramars-actions")):
    if os.path.isdir(extra) and extra not in sys.path:
        sys.path.insert(0, os.path.normpath(extra))

MODEL = "claude-opus-5-5"
PAGES = {
    "home": "Главная", "appearance": "Оформление", "network": "Сеть и VPN", "system": "Система",
    "windows": "Переезд с Windows", "games": "Игры", "phone": "Телефон", "privacy": "Приватность",
    "laptop": "Ноутбук",
}


def quick_actions():
    try:
        from astramars_actions.actions import BUILTIN
        return [{"id": a["id"], "title": a["title"], "subtitle": a.get("subtitle", "")} for a in BUILTIN]
    except Exception:  # noqa: BLE001 — помощник работает и без Быстрых действий
        return []


SYSTEM_PROMPT = """Ты — встроенный помощник AstraMars OS. Отвечай по-русски, коротко и по делу, \
простыми словами: пользователь мог только что перейти с Windows.

Про систему:
- AstraMars OS основана на Fedora Kinoite: рабочий стол KDE Plasma 6, атомарные обновления (bootc).
  Система только для чтения: программы ставятся из «AstraMars Store» (Flatpak, Flathub), а не через dnf.
  Предыдущую версию системы можно вернуть в Настройках → Система → «Откатить».
- Программы для Windows (.exe) открываются двойным щелчком через Bottles; часть программ не работает
  (защита от читов в играх, Adobe, новый Microsoft Office) — тогда предлагай замену.
- Есть «Быстрые действия» (цепочки команд одной кнопкой), «Настройки AstraMars», VPN «Ygolek VPN».

Как помогать:
- Если вопрос решается кнопкой — вызови suggest_button (можно несколько раз), и коротко скажи, что она
  сделает. Кнопку нажимает сам пользователь; не пиши, что ты уже что-то сделал.
- Чтобы узнать о компьютере (место на диске, версия, батарея, VPN), вызови get_system_info.
- Команды терминала давай только если без них никак, по одной, с пояснением. Не предлагай sudo dnf install.
- Не выдумывай пункты меню и программы, которых нет."""


def tools():
    actions = quick_actions()
    return [
        {
            "name": "get_system_info",
            "description": "Сведения о компьютере пользователя: версия системы, процессор, видеокарта, память, "
                           "место на диске, батарея, профиль питания, включён ли VPN, есть ли обновление.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "suggest_button",
            "description": "Показать пользователю кнопку под ответом. kind=quick_action — запустить Быстрое "
                           "действие (target — его id); kind=settings_page — открыть раздел Настроек AstraMars "
                           "(target — id раздела); kind=store_search — найти программу в AstraMars Store "
                           "(target — поисковый запрос, например «фоторедактор»). Быстрые действия: " +
                           "; ".join(f"{a['id']} — {a['title']}" for a in actions) +
                           ". Разделы настроек: " + "; ".join(f"{k} — {v}" for k, v in PAGES.items()) + ".",
            "input_schema": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["quick_action", "settings_page", "store_search"]},
                    "target": {"type": "string", "description": "id действия, id раздела или поисковый запрос"},
                    "label": {"type": "string", "description": "Текст на кнопке, 2–4 слова"},
                },
                "required": ["kind", "target", "label"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    ]


def system_info():
    i = system.info()
    upd = system.update_status()
    bats = power.batteries()
    vpn = network.vpn_state()
    lines = [
        f"Система: {i['name']} (ядро {i['kernel']}, Plasma {i['plasma']}, образ {i['variant']})",
        f"Процессор: {i['cpu']}; видеокарта: {i['gpu']}; память: {i['ram']}",
        f"Диск: занято {i['diskUsed']} из {i['diskTotal']} ({i['diskPercent']}%), свободно {i['diskFree']}",
        f"Включён {i['uptime']}",
        "Обновление системы: " + ("есть новая версия" if upd.get("available") else
                                  "скачано, ждёт перезагрузки" if upd.get("staged") else "новых нет или не проверялось"),
        "VPN: " + ("включён" if vpn.get("vpn") else "выключен") + (f"; прокси: {vpn['proxy']}" if vpn.get("proxy") else ""),
        f"Профиль питания: {power.profile() or 'неизвестно'}",
    ]
    for b in bats:
        lines.append(f"Батарея: {b['percent']}%, {b['status'].lower()}, здоровье {b['health']}%")
    return "\n".join(lines)


# --- Ключ ---------------------------------------------------------------------------------

def api_key():
    return os.environ.get("ANTHROPIC_API_KEY") or load_json("assistant.json").get("api_key", "")


def set_api_key(key):
    data = load_json("assistant.json")
    if key:
        data["api_key"] = key.strip()
    else:
        data.pop("api_key", None)
    save_json("assistant.json", data, private=True)


def sdk_available():
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


# --- Разговор -------------------------------------------------------------------------------

class Chat:
    """История одного разговора. send() блокирует — вызывать из рабочего потока."""

    def __init__(self):
        self.messages = []

    def reset(self):
        self.messages = []

    def send(self, text):
        """→ {"text": ответ, "buttons": [{kind, target, label}], "error": ""}"""
        if not api_key():
            return offline(text)
        try:
            import anthropic
        except ImportError:
            return {"text": "", "buttons": [], "error": "Не найдена библиотека anthropic"}

        client = anthropic.Anthropic(api_key=api_key(), max_retries=2, timeout=120)
        start = len(self.messages)
        self.messages.append({"role": "user", "content": text})
        buttons, parts, error = [], [], ""
        try:
            for _ in range(6):   # не больше шести кругов «инструмент → ответ»
                response = client.beta.messages.create(
                    model=MODEL,
                    max_tokens=16000,
                    system=SYSTEM_PROMPT,
                    tools=tools(),
                    messages=self.messages,
                    output_config={"effort": "low"},
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                )
                if response.stop_reason == "refusal":
                    del self.messages[start:]
                    return {"text": "", "buttons": [], "error": "Помощник не может ответить на этот вопрос."}
                self.messages.append({"role": "assistant", "content": response.content})
                parts += [b.text for b in response.content if b.type == "text" and b.text.strip()]
                if response.stop_reason == "pause_turn":
                    continue
                calls = [b for b in response.content if b.type == "tool_use"]
                if response.stop_reason != "tool_use" or not calls:
                    break
                results = []
                for call in calls:
                    if call.name == "get_system_info":
                        content, error = system_info(), False
                    elif call.name == "suggest_button" and isinstance(call.input, dict) and \
                            call.input.get("kind") in ("quick_action", "settings_page", "store_search"):
                        buttons.append({k: str(call.input.get(k, "")) for k in ("kind", "target", "label")})
                        content, error = "Кнопка показана пользователю.", False
                    else:
                        content, error = "Неизвестный инструмент или неверные данные.", True
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": content,
                                    "is_error": error})
                self.messages.append({"role": "user", "content": results})
        except anthropic.AuthenticationError:
            error = "Ключ API не подходит — проверьте его в Настройках → Помощник."
        except anthropic.PermissionDeniedError:
            error = "Доступ запрещён. Из России Anthropic API работает только через VPN — включите Ygolek VPN."
        except anthropic.RateLimitError:
            error = "Слишком много запросов — попробуйте через минуту."
        except anthropic.APIConnectionError:
            error = "Нет связи с сервером помощника. Проверьте интернет или включите VPN."
        except anthropic.APIStatusError as e:
            error = f"Ошибка сервера помощника ({e.status_code})."
        if error:
            del self.messages[start:]   # разговор остаётся целым: вопрос можно задать снова
            return {"text": "", "buttons": [], "error": error}
        if self.messages[-1]["role"] == "user":
            # Кончились круги на результатах инструментов — закрываем ход, чтобы история оставалась верной
            self.messages.append({"role": "assistant", "content": "…"})
        return {"text": "\n\n".join(parts).strip(), "buttons": buttons, "error": ""}


# --- Без ключа: подсказки по ключевым словам ---------------------------------------------

OFFLINE = [
    (("звук", "колонк", "наушник", "микрофон"), "Попробуйте перезапустить звуковую систему — это решает "
     "большинство проблем со звуком.", [("quick_action", "audio", "Починить звук")]),
    (("интернет", "wi-fi", "wifi", "вайфай", "сеть"), "Проверьте, какие сайты открываются, и перезапустите сеть.",
     [("settings_page", "network", "Проверить сайты"), ("quick_action", "network", "Перезапустить сеть")]),
    (("место", "диск", "памят", "очист", "мусор"), "Можно удалить ненужные файлы и посмотреть, что занимает место.",
     [("quick_action", "clean", "Очистить систему"), ("quick_action", "space", "Где место на диске")]),
    (("обнов",), "Обновления системы и программ — в одном месте.", [("settings_page", "system", "Обновления")]),
    (("windows", "exe", "виндовс", "перенес", "переех"), "Файлы, закладки и обои можно перенести с диска "
     "Windows, а программы .exe открываются двойным щелчком.", [("settings_page", "windows", "Переезд с Windows")]),
    (("игр", "steam", "nvidia", "стим"), "Игровой набор ставится одной кнопкой.", [("settings_page", "games", "Игры")]),
    (("телефон", "android", "андроид", "iphone"), "Подключите телефон через KDE Connect.",
     [("settings_page", "phone", "Телефон")]),
    (("батаре", "заряд", "ноутбук", "яркост"), "Батарея, яркость и профили питания — в разделе «Ноутбук».",
     [("settings_page", "laptop", "Ноутбук")]),
    (("цвет", "тема", "обои", "оформлен"), "Цвет акцента, тему и обои можно сменить в «Оформлении».",
     [("settings_page", "appearance", "Оформление")]),
    (("vpn", "впн", "youtube", "ютуб", "дискорд", "discord"), "Проверьте доступ к сайтам и включите Ygolek VPN.",
     [("settings_page", "network", "Сеть и VPN")]),
    (("фото", "редакт", "офис", "word", "excel", "браузер", "музык", "видео"), "Подходящие программы есть в "
     "AstraMars Store.", [("store_search", "", "Найти в Магазине")]),
]


def offline(text):
    low = text.lower()
    for words, answer, buttons in OFFLINE:
        if any(w in low for w in words):
            return {"text": answer + "\n\nЧтобы помощник отвечал на любые вопросы, добавьте ключ Anthropic API "
                    "в Настройках → Помощник.",
                    "buttons": [{"kind": k, "target": t or text, "label": l} for k, t, l in buttons], "error": ""}
    return {"text": "Без ключа API я понимаю только простые просьбы: «нет звука», «мало места», «обновить "
            "систему», «перенести файлы с Windows», «настроить игры». Добавьте ключ Anthropic API в "
            "Настройках → Помощник, и я смогу отвечать на любые вопросы.", "buttons":
            [{"kind": "settings_page", "target": "assistant", "label": "Добавить ключ"}], "error": ""}


if DEV and __name__ == "__main__":
    print(system_info())
