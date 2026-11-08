"""Связка интерфейса (QML) с серверами, подписками и службой VPN."""

import json
import os
import socket
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from . import __version__, SINGBOX_VERSION, links, service, singbox, store

PING_UNKNOWN, PING_UDP, PING_FAIL = -1, -2, -3
AUTOSTART_PATH = os.path.expanduser("~/.config/autostart/astramars-vpn.desktop")


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _tcp_ping(host: str, port: int) -> int:
    try:
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=3):
            return int((time.perf_counter() - start) * 1000)
    except OSError:
        return PING_FAIL


def _fmt_speed(bps: float) -> str:
    for unit, size in (("ГБ/с", 1 << 30), ("МБ/с", 1 << 20), ("КБ/с", 1 << 10)):
        if bps >= size:
            return f"{bps / size:.1f} {unit}".replace(".", ",")
    return f"{int(bps)} Б/с"


def _fmt_bytes(n: float) -> str:
    for unit, size in (("ТБ", 1 << 40), ("ГБ", 1 << 30), ("МБ", 1 << 20)):
        if n >= size:
            return f"{n / size:.1f} {unit}".replace(".", ",")
    return f"{int(n / 1024)} КБ"


# Панели (Remnawave, Marzban, 3x-ui и др.) выбирают формат подписки по User-Agent.
# Сначала просим обычный список ссылок, затем формат ядра sing-box, затем Clash/Mihomo.
SUBSCRIPTION_AGENTS = (
    f"AstraMarsVPN/{__version__}",
    f"sing-box/{SINGBOX_VERSION}",
    "clash.meta",
)


def _download(url: str, agent: str):
    req = urllib.request.Request(url, headers={"User-Agent": agent, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read(5_000_000).decode("utf-8", "replace"), r.headers
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError):
        # Сервер подписки недоступен напрямую — пробуем через наш прокси, если он запущен
        if not _port_open(singbox.MIXED_PORT):
            raise
        proxy = f"http://127.0.0.1:{singbox.MIXED_PORT}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        with opener.open(req, timeout=20) as r:
            return r.read(5_000_000).decode("utf-8", "replace"), r.headers


def fetch_subscription(url: str):
    last_error = None
    for agent in SUBSCRIPTION_AGENTS:
        body, headers = _download(url, agent)
        try:
            servers, errors = links.parse_subscription(body)
        except links.LinkError as e:
            last_error = e
            continue
        if not servers and errors and agent != SUBSCRIPTION_AGENTS[-1]:
            # Все серверы в этом формате не подошли (например, XHTTP) — пробуем другой
            last_error = links.LinkError(errors[0])
            continue
        return {
            "servers": servers,
            "errors": errors,
            "info": links.parse_userinfo(headers.get("subscription-userinfo", "")),
            "title": links.parse_title(headers.get("profile-title", "")),
        }
    raise last_error or links.LinkError("в подписке нет серверов")


class Backend(QObject):
    serversChanged = Signal()
    selectedChanged = Signal()
    statusChanged = Signal()
    settingsChanged = Signal()
    subscriptionsChanged = Signal()
    trafficChanged = Signal()
    busyChanged = Signal()
    toast = Signal(str)
    showWindowRequested = Signal()

    # Результаты фоновых задач (приходят в главный поток)
    _pingDone = Signal(str, int)
    _connectDone = Signal(bool, str)
    _subsDone = Signal(object)
    _activeChecked = Signal(bool)
    _trafficRead = Signal(float, float)

    def __init__(self, svc=None):
        super().__init__()
        self._svc = svc or service.create()
        self._data = store.load()
        self._pings = {}
        self._status = "off"
        self._error = ""
        self._since = 0.0
        self._down = self._up = 0.0
        self._last_totals = None
        self._busy = False
        self._pool = ThreadPoolExecutor(max_workers=8)

        self._pingDone.connect(self._on_ping)
        self._connectDone.connect(self._on_connect_done)
        self._subsDone.connect(self._on_subs_done)
        self._activeChecked.connect(self._on_active_checked)
        self._trafficRead.connect(self._on_traffic)

        self._status_timer = QTimer(self, interval=2500, timeout=self._poll_status)
        self._traffic_timer = QTimer(self, interval=1000, timeout=self._poll_traffic)
        self._status_timer.start()
        self._traffic_timer.start()

        if self._svc.is_active():
            self._status, self._since = "on", self._svc.active_since()
        store.save(self._data)

    # --- свойства для QML -----------------------------------------------------------

    @Property("QVariantList", notify=serversChanged)
    def servers(self):
        return [{
            "id": s["id"],
            "name": s["name"],
            "protocol": links.PROTOCOL_LABELS.get(s["protocol"], s["protocol"]),
            "address": f"{s['host']}:{s['port']}",
            "ping": self._pings.get(s["id"], PING_UDP if s["protocol"] in links.UDP_PROTOCOLS else PING_UNKNOWN),
            "sub": s.get("sub") or "",
        } for s in self._data["servers"]]

    @Property(str, notify=selectedChanged)
    def selected(self):
        return self._data["selected"]

    @Property("QVariantMap", notify=selectedChanged)
    def current(self):
        s = self._server(self._data["selected"])
        if not s:
            return {}
        return {"name": s["name"], "protocol": links.PROTOCOL_LABELS.get(s["protocol"], s["protocol"]),
                "address": f"{s['host']}:{s['port']}"}

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(str, notify=statusChanged)
    def error(self):
        return self._error

    @Property(float, notify=statusChanged)
    def connectedSince(self):
        return self._since * 1000

    @Property(str, notify=trafficChanged)
    def downSpeed(self):
        return _fmt_speed(self._down)

    @Property(str, notify=trafficChanged)
    def upSpeed(self):
        return _fmt_speed(self._up)

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=settingsChanged)
    def mode(self):
        return self._data["mode"]

    @Property(bool, notify=settingsChanged)
    def bypassRu(self):
        return self._data["bypass_ru"]

    @Property(bool, notify=settingsChanged)
    def autoconnect(self):
        return self._data["autoconnect"]

    @Property(bool, notify=settingsChanged)
    def autostart(self):
        return os.path.exists(AUTOSTART_PATH)

    @Property(str, constant=True)
    def version(self):
        return f"AstraMars VPN {__version__} · ядро sing-box {SINGBOX_VERSION}"

    @Property("QVariantList", notify=subscriptionsChanged)
    def subscriptions(self):
        result = []
        for sub in self._data["subscriptions"]:
            info = sub.get("info") or {}
            used = info.get("upload", 0) + info.get("download", 0)
            total = info.get("total", 0)
            expire = info.get("expire", 0)
            parts = []
            if total:
                parts.append(f"{_fmt_bytes(used)} из {_fmt_bytes(total)}")
            elif used:
                parts.append(f"использовано {_fmt_bytes(used)}")
            if expire:
                parts.append("до " + time.strftime("%d.%m.%Y", time.localtime(expire)))
            count = sum(1 for s in self._data["servers"] if s.get("sub") == sub["id"])
            result.append({
                "id": sub["id"],
                "name": sub.get("title") or (sub["url"].split("/")[2] if "://" in sub["url"] else sub["url"]),
                "details": " · ".join(parts) or f"серверов: {count}",
                "usage": (used / total) if total else -1,
                "count": count,
            })
        return result

    # --- действия ------------------------------------------------------------------

    @Slot()
    def toggleConnection(self):
        if self._status in ("on", "connecting"):
            self.disconnect()
        else:
            self.connect_()

    @Slot()
    def connect_(self):
        server = self._server(self._data["selected"])
        if not server:
            self.toast.emit("Сначала добавьте сервер")
            return
        self._set_status("connecting")
        self._pool.submit(self._do_connect, server, self._data["mode"], self._data["bypass_ru"])

    @Slot()
    def disconnect(self):
        def work():
            try:
                self._svc.stop()
                self._svc.refresh_system_proxy()
                self._connectDone.emit(False, "")
            except service.ServiceError as e:
                self._connectDone.emit(False, str(e))
        self._pool.submit(work)

    @Slot(str)
    def selectServer(self, server_id):
        if server_id == self._data["selected"]:
            return
        self._data["selected"] = server_id
        self._save()
        self.selectedChanged.emit()
        if self._status == "on":
            self.connect_()

    @Slot(str)
    def removeServer(self, server_id):
        self._data["servers"] = [s for s in self._data["servers"] if s["id"] != server_id]
        if self._data["selected"] == server_id:
            self._data["selected"] = self._data["servers"][0]["id"] if self._data["servers"] else ""
            self.selectedChanged.emit()
        self._save()
        self.serversChanged.emit()

    @Slot(result=str)
    def clipboardText(self):
        return QGuiApplication.clipboard().text()

    @Slot(str)
    def addFromText(self, text):
        text = (text or "").strip()
        if not text:
            self.toast.emit("Вставьте ссылку или адрес подписки")
            return
        # Адреса подписок (https://… и ссылки-приглашения приложений) — отдельно от ссылок на серверы
        urls, rest = [], []
        for line in text.splitlines():
            url = links.extract_subscription_url(line)
            (urls if url else rest).append(url or line)
        if urls:
            known = {sub["url"] for sub in self._data["subscriptions"]}
            for url in urls:
                if url not in known:
                    self._data["subscriptions"].append({"id": uuid.uuid4().hex[:8], "url": url})
                    known.add(url)
            self._save()
            self.subscriptionsChanged.emit()
            self.toast.emit("Загружаю подписку…")
            self.updateSubscriptions()
            if not "\n".join(rest).strip():
                return
            text = "\n".join(rest)
        servers, errors = links.parse_many(text)
        added = self._merge(servers, sub_id=None)
        msg = f"Добавлено серверов: {added}" if added else "Новых серверов нет"
        if errors:
            msg += f". Не удалось разобрать: {len(errors)} — {errors[0]}"
        self.toast.emit(msg)
        self.pingAll()

    @Slot()
    def updateSubscriptions(self):
        subs = list(self._data["subscriptions"])
        if not subs:
            self.toast.emit("Подписок пока нет")
            return
        self._set_busy(True)

        def work():
            results = []
            for sub in subs:
                name = sub.get("title") or (sub["url"].split("/")[2] if "://" in sub["url"] else sub["url"])
                try:
                    results.append((sub["id"], fetch_subscription(sub["url"]), ""))
                except links.LinkError as e:
                    results.append((sub["id"], None, f"«{name}»: {e}"))
                except urllib.error.HTTPError as e:
                    results.append((sub["id"], None, f"«{name}»: сервер ответил ошибкой {e.code}"))
                except (urllib.error.URLError, OSError, ValueError):
                    results.append((sub["id"], None, f"«{name}» не скачалась — нет связи с сервером подписки"))
            self._subsDone.emit(results)
        self._pool.submit(work)

    @Slot(str)
    def removeSubscription(self, sub_id):
        self._data["subscriptions"] = [s for s in self._data["subscriptions"] if s["id"] != sub_id]
        self._data["servers"] = [s for s in self._data["servers"] if s.get("sub") != sub_id]
        if not self._server(self._data["selected"]):
            self._data["selected"] = self._data["servers"][0]["id"] if self._data["servers"] else ""
            self.selectedChanged.emit()
        self._save()
        self.serversChanged.emit()
        self.subscriptionsChanged.emit()

    @Slot()
    def pingAll(self):
        for s in self._data["servers"]:
            if s["protocol"] in links.UDP_PROTOCOLS:
                continue
            self._pings[s["id"]] = PING_UNKNOWN
            self._pool.submit(lambda s=s: self._pingDone.emit(s["id"], _tcp_ping(s["host"], s["port"])))
        self.serversChanged.emit()

    @Slot(str)
    def setMode(self, mode):
        if mode not in ("tun", "proxy") or mode == self._data["mode"]:
            return
        self._data["mode"] = mode
        self._save()
        self.settingsChanged.emit()
        if self._status == "on":
            self.connect_()

    @Slot(bool)
    def setBypassRu(self, value):
        self._data["bypass_ru"] = bool(value)
        self._save()
        self.settingsChanged.emit()
        if self._status == "on":
            self.connect_()

    @Slot(bool)
    def setAutoconnect(self, value):
        self._data["autoconnect"] = bool(value)
        self._save()
        self.settingsChanged.emit()

    @Slot(bool)
    def setAutostart(self, value):
        if value:
            os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
            with open(AUTOSTART_PATH, "w", encoding="utf-8") as f:
                f.write("[Desktop Entry]\nType=Application\nName=AstraMars VPN\n"
                        "Exec=astramars-vpn --minimized\nIcon=astramars-vpn\nX-GNOME-Autostart-enabled=true\n")
        elif os.path.exists(AUTOSTART_PATH):
            os.remove(AUTOSTART_PATH)
        self.settingsChanged.emit()

    def start(self):
        """Вызывается после загрузки интерфейса."""
        self.pingAll()
        if self._data["autoconnect"] and self._status == "off" and self._data["selected"]:
            self.connect_()
        if self._data["subscriptions"]:
            self.updateSubscriptions()

    def shutdown(self):
        self._status_timer.stop()
        self._traffic_timer.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)

    # --- внутреннее ------------------------------------------------------------------

    def _server(self, server_id):
        return next((s for s in self._data["servers"] if s["id"] == server_id), None)

    def _save(self):
        store.save(self._data)

    def _set_status(self, status, error=""):
        self._status, self._error = status, error
        if status == "on" and not self._since:
            self._since = time.time()
        if status != "on":
            self._since = 0.0
            self._down = self._up = 0.0
            self._last_totals = None
            self.trafficChanged.emit()
        self.statusChanged.emit()

    def _set_busy(self, value):
        self._busy = value
        self.busyChanged.emit()

    def _merge(self, servers, sub_id):
        known = {s["id"] for s in self._data["servers"]}
        added = 0
        for s in servers:
            s = dict(s, sub=sub_id)
            if s["id"] not in known:
                self._data["servers"].append(s)
                known.add(s["id"])
                added += 1
        if not self._data["selected"] and self._data["servers"]:
            self._data["selected"] = self._data["servers"][0]["id"]
            self.selectedChanged.emit()
        self._save()
        self.serversChanged.emit()
        return added

    def _do_connect(self, server, mode, bypass):
        try:
            cfg = singbox.build_config(server["outbound"], mode=mode, bypass_ru=bypass,
                                       api_secret=self._data["api_secret"])
            self._svc.write_config(cfg)
            ok, err = self._svc.check_config()
            if not ok:
                self._connectDone.emit(False, "Ошибка в настройках сервера: " + err)
                return
            self._svc.restart()
            for _ in range(40):
                time.sleep(0.25)
                if self._svc.is_active() and (os.environ.get("ASTRAMARS_VPN_DEV") or _port_open(singbox.MIXED_PORT)):
                    break
            else:
                self._connectDone.emit(False, self._svc.last_error() or "Ядро не запустилось")
                return
            self._svc.refresh_system_proxy()
            self._connectDone.emit(True, "")
        except service.ServiceError as e:
            self._connectDone.emit(False, str(e))
        except OSError as e:
            self._connectDone.emit(False, f"Ошибка: {e}")

    def _on_connect_done(self, ok, error):
        if ok:
            self._since = 0.0
            self._set_status("on")
        else:
            self._set_status("error" if error else "off", error)
            if error:
                self.toast.emit(error)

    def _on_ping(self, server_id, ms):
        self._pings[server_id] = ms
        self.serversChanged.emit()

    def _on_subs_done(self, results):
        self._set_busy(False)
        total_added, problems = 0, []
        for sub_id, result, error in results:
            sub = next((s for s in self._data["subscriptions"] if s["id"] == sub_id), None)
            if sub is None:
                continue
            if error:
                problems.append(error)
                continue
            # Подписка заменяет свои серверы целиком
            new_ids = {s["id"] for s in result["servers"]}
            self._data["servers"] = [s for s in self._data["servers"] if s.get("sub") != sub_id or s["id"] in new_ids]
            total_added += self._merge(result["servers"], sub_id)
            sub["info"] = result["info"]
            if result["title"]:
                sub["title"] = result["title"]
            sub["updated"] = int(time.time())
            problems += result["errors"][:1]
        if not self._server(self._data["selected"]):
            self._data["selected"] = self._data["servers"][0]["id"] if self._data["servers"] else ""
            self.selectedChanged.emit()
        self._save()
        self.serversChanged.emit()
        self.subscriptionsChanged.emit()
        ok_count = sum(1 for _, result, _ in results if result)
        if ok_count:
            msg = f"Подписки обновлены, новых серверов: {total_added}"
            if problems:
                msg += f". {problems[0]}"
        else:
            msg = "Подписка " + problems[0] if problems else "Подписки не обновились"
        self.toast.emit(msg)
        self.pingAll()

    def _poll_status(self):
        if self._status == "connecting":
            return
        self._pool.submit(lambda: self._activeChecked.emit(self._svc.is_active()))

    def _on_active_checked(self, active):
        if self._status == "connecting":
            return
        if active and self._status != "on":
            self._since = self._svc.active_since()
            self._set_status("on")
        elif not active and self._status == "on":
            self._set_status("error", "Соединение прервалось")
            self.toast.emit("Соединение прервалось")

    def _poll_traffic(self):
        if self._status != "on":
            return
        secret = self._data["api_secret"]

        def work():
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{singbox.API_PORT}/connections",
                                             headers={"Authorization": f"Bearer {secret}"})
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(req, timeout=0.8) as r:
                    data = json.load(r)
                self._trafficRead.emit(float(data.get("downloadTotal", 0)), float(data.get("uploadTotal", 0)))
            except (OSError, ValueError):
                pass
        self._pool.submit(work)

    def _on_traffic(self, down_total, up_total):
        now = time.monotonic()
        if self._last_totals:
            t0, d0, u0 = self._last_totals
            dt = max(now - t0, 0.001)
            self._down = max(down_total - d0, 0) / dt
            self._up = max(up_total - u0, 0) / dt
            self.trafficChanged.emit()
        self._last_totals = (now, down_total, up_total)
