"""Самотест Настроек AstraMars при сборке образа.

  python3 settings_selftest.py /usr/lib/astramars-settings

Проверяет без сети и без прав администратора:
  - переезд с Windows на поддельном диске: поиск, копирование, закладки Chrome и Firefox, обои;
  - оценку программ .exe;
  - помощника против подставного сервера API: цикл инструментов, кнопки, ошибки, офлайн-режим;
  - помощника администратора: разбирается Python, отказывается работать без root.
"""

import json
import os
import py_compile
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
HOME = tempfile.mkdtemp(prefix="settings-check-")
os.environ.update(ASTRAMARS_SETTINGS_DEV="1", ASTRAMARS_SETTINGS_HOME=HOME, XDG_CONFIG_HOME=os.path.join(HOME, ".config"))
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, "vendor"))

from astramars_settings import assistant, exe, windows  # noqa: E402

# --- Переезд с Windows ------------------------------------------------------------------------
u = os.path.join(HOME, "fake-windows", "Users", "Artem")
for d in ("Desktop", "Documents/Work", "Pictures", "Downloads"):
    os.makedirs(os.path.join(u, d))
os.makedirs(os.path.join(HOME, "fake-windows", "Users", "Public"))
open(os.path.join(u, "Documents/Work/report.txt"), "w").write("x" * 5000)
open(os.path.join(u, "Desktop/desktop.ini"), "w").write("skip")
open(os.path.join(u, "Desktop/link.lnk"), "w").write("skip")
open(os.path.join(u, "Pictures/cat.jpg"), "wb").write(b"\xff" * 20000)
chrome = os.path.join(u, "AppData/Local/Google/Chrome/User Data/Default")
os.makedirs(chrome)
json.dump({"roots": {"bookmark_bar": {"type": "folder", "name": "Панель", "children": [
    {"type": "url", "name": "Госуслуги", "url": "https://gosuslugi.ru"},
    {"type": "folder", "name": "Работа", "children": [{"type": "url", "name": "GitHub <dev>", "url": "https://github.com"}]}]}}},
    open(os.path.join(chrome, "Bookmarks"), "w", encoding="utf-8"))
fx = os.path.join(u, "AppData/Roaming/Mozilla/Firefox/Profiles/abc.default")
os.makedirs(fx)
con = sqlite3.connect(os.path.join(fx, "places.sqlite"))
con.executescript("""CREATE TABLE moz_places(id INTEGER PRIMARY KEY, url TEXT);
CREATE TABLE moz_bookmarks(id INTEGER PRIMARY KEY, type INT, fk INT, parent INT, position INT, title TEXT);
INSERT INTO moz_places VALUES (1,'https://ya.ru'),(2,'place:sort=8');
INSERT INTO moz_bookmarks VALUES (1,2,NULL,0,0,''),(2,2,NULL,1,0,'toolbar'),(3,1,1,2,0,'Яндекс'),(4,1,2,2,1,'Недавние');""")
con.commit()
con.close()
os.makedirs(os.path.join(u, "AppData/Roaming/Microsoft/Windows/Themes"))
open(os.path.join(u, windows.WALLPAPER), "wb").write(b"\xff\xd8jpeg")

found, errors = windows.find_windows()
assert [x["name"] for x in found[0]["users"]] == ["Artem"], found
assert windows.plan(u, ["desktop", "documents", "pictures"]) == (2, 25000)
copied, failed, cancelled = windows.copy_folders(u, ["desktop", "documents", "pictures"], lambda p, t: None)
assert (copied, failed, cancelled) == (2, 0, ""), (copied, failed, cancelled)
assert os.path.isfile(os.path.join(HOME, "Documents", windows.SUBDIR, "Work", "report.txt"))
path, n = windows.export_bookmarks(u)
text = open(path, encoding="utf-8").read()
assert n == 3 and "GitHub &lt;dev&gt;" in text and "Панель закладок" in text and "place:" not in text, text
assert windows.import_wallpaper(u)
print("переезд с Windows: ок")

# --- .exe ------------------------------------------------------------------------------------------
for name, ok in (("Photoshop_2024.exe", False), ("reset_tool.exe", True), ("notepad++.exe", True),
                 ("DiscordSetup.exe", False), ("OfficeSetup.exe", False), ("VALORANT Installer.exe", False)):
    assert exe.verdict(name)["ok"] == ok, name
print("оценка .exe: ок")

# --- Помощник ---------------------------------------------------------------------------------------
requests, script = [], []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        requests.append({"path": self.path, "beta": self.headers.get("anthropic-beta") or "", "body": body})
        status, payload = script.pop(0)
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


srv = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ.update(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{srv.server_port}", ANTHROPIC_API_KEY="test-key",
                  NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(var, None)


def msg(content, stop):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": assistant.MODEL, "content": content,
            "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 5}}


assert assistant.sdk_available(), "нет библиотеки anthropic"
chat = assistant.Chat()
script += [
    (200, msg([{"type": "text", "text": "Сейчас посмотрю."},
               {"type": "tool_use", "id": "tu_1", "name": "get_system_info", "input": {}},
               {"type": "tool_use", "id": "tu_2", "name": "suggest_button",
                "input": {"kind": "quick_action", "target": "audio", "label": "Починить звук"}}], "tool_use")),
    (200, msg([{"type": "text", "text": "Нажмите кнопку — PipeWire перезапустится."}], "end_turn")),
]
r = chat.send("нет звука")
assert r["buttons"] == [{"kind": "quick_action", "target": "audio", "label": "Починить звук"}], r
assert "PipeWire" in r["text"] and not r["error"], r
first, second = requests[0], requests[1]
assert first["body"]["model"] == "claude-opus-5-5" and first["body"]["fallbacks"] == "default", first["body"]
assert "server-side-fallback-2026-07-01" in first["beta"], first["beta"]
tools = {t["name"]: t for t in first["body"]["tools"]}
assert "audio" in tools["suggest_button"]["description"], "Быстрые действия не попали в описание инструмента"
results = second["body"]["messages"][-1]["content"]
assert [x["tool_use_id"] for x in results] == ["tu_1", "tu_2"] and "Диск" in results[0]["content"]
script.append((401, {"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}))
r = chat.send("ещё вопрос")
assert "Ключ" in r["error"] and len(chat.messages) == 4, (r, len(chat.messages))
script.append((200, msg([{"type": "text", "text": "Ок"}], "end_turn")))
assert chat.send("ещё раз")["text"] == "Ок"
assert [m["role"] for m in requests[-1]["body"]["messages"]] == ["user", "assistant", "user", "assistant", "user"]
del os.environ["ANTHROPIC_API_KEY"]
assert assistant.Chat().send("мало места на диске")["buttons"][0]["target"] == "clean"
srv.shutdown()
print("помощник: ок")

# --- Помощник администратора ------------------------------------------------------------------------
helper = "/usr/libexec/astramars-settings-helper"
if os.path.exists(helper):
    py_compile.compile(helper, cfile=os.path.join(HOME, "helper.pyc"), doraise=True)
    if os.geteuid() == 0:
        p = subprocess.run([helper, "nonsense"], capture_output=True, text=True)
        assert p.returncode == 2, p
        p = subprocess.run([helper, "snapshot", "delete", "../../etc"], capture_output=True, text=True)
        assert p.returncode != 0 and "имя" in (p.stderr + p.stdout), p
        p = subprocess.run([helper, "dns", "evil"], capture_output=True, text=True)
        assert p.returncode != 0, p
    print("помощник администратора: ок")

print("Самотест Настроек пройден")
