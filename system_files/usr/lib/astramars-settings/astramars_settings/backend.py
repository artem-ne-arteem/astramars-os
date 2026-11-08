"""Мост между QML и модулями настроек. Долгие дела — в фоновых потоках, ход сообщается сигналом job."""

import os
import sys
import threading

from PySide6.QtCore import QObject, QUrl, Signal, Slot

from . import appearance, assistant, exe, games, network, phone, power, privacy, system, windows
from .util import DEV, spawn

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.normpath(os.path.join(HERE, "..", "..", "astramars-store"))
if os.path.isdir(STORE) and STORE not in sys.path:
    sys.path.insert(0, STORE)
if DEV:
    os.environ.setdefault("ASTRAMARS_STORE_DEV", "1")


def _flatpak():
    from astramars_store.flatpak import create
    return create()


class Backend(QObject):
    # id задачи, состояние (running|done|error), процент (-1 — неизвестно), текст
    job = Signal(str, str, int, str)
    siteResult = Signal("QVariantMap")
    windowsFound = Signal("QVariantMap")
    chatReply = Signal("QVariantMap")
    openPage = Signal(str)
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._chat = assistant.Chat()
        self._busy = set()
        self._cancel = set()

    # --- служебное ---------------------------------------------------------------------
    def _run(self, job_id, fn, *args):
        """fn(report, *args) в фоне; report(процент, текст). Возврат fn — итоговый текст."""
        if job_id in self._busy:
            return False
        self._busy.add(job_id)
        self._cancel.discard(job_id)

        def report(pct, text=""):
            self.job.emit(job_id, "running", int(pct), str(text))

        def work():
            try:
                result = fn(report, *args)
                self.job.emit(job_id, "done", 100, str(result or ""))
            except Exception as e:  # noqa: BLE001 — показать любую ошибку человеку
                self.job.emit(job_id, "error", -1, str(e) or e.__class__.__name__)
            finally:
                self._busy.discard(job_id)
        report(-1, "")
        threading.Thread(target=work, daemon=True).start()
        return True

    @Slot(str, result=bool)
    def busy(self, job_id):
        return job_id in self._busy

    @Slot(str)
    def cancel(self, job_id):
        self._cancel.add(job_id)

    @staticmethod
    def _ok(result):
        ok, text = result
        if not ok:
            raise RuntimeError(text or "не получилось")
        return text

    @Slot(str)
    def openKde(self, module):
        system.open_kde_settings(module)

    @Slot(str)
    def openPath(self, path):
        spawn("dolphin", "--new-window", path)

    @Slot(str)
    def storeSearch(self, query):
        spawn("astramars-store", "--search", query)

    # --- Главная и Система ---------------------------------------------------------------
    @Slot(result="QVariantMap")
    def info(self):
        return system.info()

    @Slot(result="QVariantMap")
    def updateStatus(self):
        return system.update_status()

    @Slot()
    def checkUpdates(self):
        system.update_check()

    @Slot()
    def applyUpdate(self):
        system.update_apply()

    @Slot()
    def reboot(self):
        system.reboot()

    @Slot()
    def rollback(self):
        self._run("rollback", lambda r: self._ok(system.rollback()) and
                  "Готово: после перезагрузки включится предыдущая версия системы.")

    @Slot(result="QVariantMap")
    def snapshotsInfo(self):
        ok, reason = system.snapshots_available()
        return {"available": ok, "reason": reason, "timer": system.snapshot_timer_enabled() if ok else False,
                "list": system.snapshots() if ok else []}

    @Slot()
    def createSnapshot(self):
        from .util import helper

        def work(report):
            report(-1, "Делаю снимок…")
            self._ok(helper("snapshot", "create"))
            self.changed.emit("snapshots")
            return "Снимок готов"
        self._run("snapshot", work)

    @Slot(str)
    def deleteSnapshot(self, name):
        from .util import helper

        def work(report):
            self._ok(helper("snapshot", "delete", name))
            self.changed.emit("snapshots")
            return "Снимок удалён"
        self._run("snapshot", work)

    @Slot(bool)
    def setSnapshotTimer(self, on):
        from .util import helper
        self._run("snapshot-timer", lambda r: (self._ok(helper("snapshot", "timer", "on" if on else "off")),
                                               self.changed.emit("snapshots")) and "")

    @Slot(str)
    def openSnapshot(self, name):
        system.open_snapshot(name)

    # --- Оформление ------------------------------------------------------------------------
    @Slot(result="QVariantList")
    def accents(self):
        return appearance.ACCENTS

    @Slot(result="QVariantMap")
    def appearance(self):
        return {"accent": appearance.accent(), "scheme": appearance.scheme(), "daytime": appearance.daytime_enabled()}

    @Slot(str)
    def setAccent(self, color):
        if appearance.set_accent(color):
            self.changed.emit("accent")

    @Slot(str)
    def setScheme(self, kind):
        self._run("scheme", lambda r: appearance.set_scheme(kind) and self.changed.emit("appearance"))

    @Slot(bool)
    def setDaytime(self, on):
        self._run("daytime", lambda r: (appearance.set_daytime(on), self.changed.emit("appearance")) and "")

    @Slot()
    def addClock(self):
        self._run("clock", lambda r: "Часы добавлены на рабочий стол" if appearance.add_clock_widget()
                  else self._ok((False, "рабочий стол не ответил")))

    @Slot()
    def openWallpapers(self):
        appearance.open_wallpaper_settings()

    # --- Сеть -------------------------------------------------------------------------------
    @Slot(result="QVariantList")
    def dnsPresets(self):
        return network.DNS_PRESETS

    @Slot(result=str)
    def dnsCurrent(self):
        return network.dns_current()

    @Slot(str)
    def setDns(self, preset):
        def work(report):
            report(-1, "Меняю DNS…")
            self._ok(network.set_dns(preset))
            self.changed.emit("dns")
            return "DNS изменён"
        self._run("dns", work)

    @Slot(result="QVariantList")
    def sites(self):
        return network.SITES

    @Slot()
    def checkSites(self):
        def work(report):
            network.check_sites(self.siteResult.emit)
            return ""
        self._run("sites", work)

    @Slot(result="QVariantMap")
    def vpnState(self):
        return network.vpn_state()

    @Slot()
    def openVpn(self):
        network.open_vpn()

    # --- Переезд с Windows ---------------------------------------------------------------------
    @Slot()
    def windowsScan(self):
        def work(report):
            report(-1, "Ищу диск Windows…")
            found, errors = windows.find_windows()
            self.windowsFound.emit({"systems": found, "errors": errors,
                                    "automount": windows.automount_enabled()})
            return ""
        self._run("winscan", work)

    @Slot(result="QVariantList")
    def windowsFolders(self):
        return [{"id": f[0], "title": f[4]} for f in windows.FOLDERS]

    @Slot(str, "QVariantList", bool, bool)
    def migrate(self, user_path, folders, bookmarks, wallpaper):
        def work(report):
            notes = []
            if folders:
                copied, failed, cancelled = windows.copy_folders(
                    user_path, list(folders), report, lambda: "migrate" in self._cancel)
                if cancelled:
                    return "Перенос остановлен. Уже скопированные файлы остались на месте."
                notes.append(f"Файлы: {copied}" + (f" (не удалось: {failed})" if failed else ""))
            if bookmarks:
                report(-1, "Переношу закладки…")
                path, count = windows.export_bookmarks(user_path)
                notes.append(f"Закладки: {count} — откройте в браузере «Импорт закладок из HTML»" if count
                             else "Закладок не нашлось")
            if wallpaper:
                notes.append("Обои Windows установлены" if windows.import_wallpaper(user_path) else
                             "Обоев Windows не нашлось")
            return " · ".join(notes) or "Готово"
        self._run("migrate", work)

    @Slot(str, bool)
    def setWindowsAutomount(self, uuid, on):
        windows.set_automount(uuid, on)

    @Slot(result=str)
    def migratedFolder(self):
        from .util import xdg_dir
        return os.path.join(xdg_dir("DOCUMENTS", "Documents"), windows.SUBDIR)

    # --- .exe ----------------------------------------------------------------------------------
    @Slot(str, result="QVariantMap")
    def exeInfo(self, path):
        v = exe.verdict(path)
        v.update(name=os.path.basename(path), bottles=exe.bottles_installed())
        return v

    @Slot(str)
    def exeRun(self, path):
        def work(report):
            if not exe.bottles_installed():
                fp = _flatpak()
                fp.ensure_flathub()
                fp.install(exe.BOTTLES, lambda p, d: report(p, "Устанавливаю Bottles · " + (d or "")))
            exe.prepare(path, lambda t: report(-1, t))
            report(-1, "Запускаю…")
            exe.run(path)
            return "Программа запускается — первый раз это может занять минуту"
        self._run("exe", work)

    @Slot()
    def openBottles(self):
        exe.open_bottles()

    # --- Игры ------------------------------------------------------------------------------------
    @Slot(result="QVariantMap")
    def gamesInfo(self):
        installed = _flatpak().installed()
        return {
            "gpus": system.gpus(), "nvidia": games.nvidia_present(), "variant": games.variant(),
            "kit": [dict(k, installed=k["id"] in installed) for k in games.KIT],
            "steam": games.STEAM in installed,
            "mangohud": games.mangohud_enabled(), "gameMode": games.game_mode(),
            "gamemode": games.gamemode_available(), "secureBoot": games.secure_boot(),
            "switch": games.switch_status(),
        }

    @Slot()
    def installKit(self):
        def work(report):
            fp = _flatpak()
            fp.ensure_flathub()
            todo = [k for k in games.KIT if k["id"] not in fp.installed()]
            for n, k in enumerate(todo):
                fp.install(k["id"], lambda p, d, n=n, k=k: report(
                    int((n + p / 100) / len(todo) * 100), f"{k['name']} · {p}%" + (f" · {d}" if d else "")))
            ref = games.mangohud_ref()
            if ref and not DEV:
                report(-1, "MangoHud…")
                try:
                    fp.install(ref, lambda p, d: report(p, f"MangoHud · {p}%"))
                except Exception:  # noqa: BLE001 — без MangoHud набор всё равно полезен
                    pass
            self.changed.emit("games")
            return "Игровой набор установлен"
        self._run("kit", work)

    @Slot(bool)
    def setMangoHud(self, on):
        games.set_mangohud(on)
        self.changed.emit("games")

    @Slot(bool)
    def setGameMode(self, on):
        games.set_game_mode(on)
        self.changed.emit("games")
        self.changed.emit("laptop")

    @Slot(str)
    def switchImage(self, kind):
        self._run("image", lambda r: self._ok(games.switch_image(kind)) and
                  "Загрузка новой версии системы началась — это займёт 10–30 минут")

    @Slot()
    def mokEnroll(self):
        def work(report):
            text = self._ok(games.mok_enroll())
            return ("Ключ уже добавлен" if text == "already" else
                    "Готово. При перезагрузке появится синий экран: Enroll MOK → Continue → Yes, "
                    "пароль universalblue → Reboot")
        self._run("mok", work)

    # --- Телефон -----------------------------------------------------------------------------------
    @Slot(result="QVariantMap")
    def phoneInfo(self):
        return {"installed": phone.installed(), "devices": phone.devices() if phone.installed() else [],
                "qr": phone.qr(), "iosUrl": phone.IOS_URL, "androidUrl": phone.ANDROID_URL}

    @Slot(str, str)
    def phoneAction(self, action, dev):
        fn = {"pair": phone.pair, "unpair": phone.unpair, "ring": phone.ring, "ping": phone.ping}.get(action)

        def work(report):
            if action == "refresh":
                phone.refresh()
            elif fn:
                ok, out = fn(dev)
                if not ok:
                    raise RuntimeError(out.splitlines()[-1] if out else "телефон не ответил")
            self.changed.emit("phone")
            return {"pair": "Подтвердите на телефоне", "ring": "Телефон звонит", "ping": "Отправлено"}.get(action, "")
        self._run("phone", work)

    @Slot(str, str)
    def phoneShare(self, dev, url):
        path = QUrl(url).toLocalFile() if url.startswith("file:") else url
        self._run("phone", lambda r: self._ok(phone.share(dev, path)) or "Файл отправлен")

    @Slot()
    def openKdeConnect(self):
        phone.open_app()

    # --- Приватность ----------------------------------------------------------------------------------
    @Slot(result="QVariantMap")
    def privacyInfo(self):
        return {"telemetry": privacy.telemetry(), "mic": privacy.microphone_users(),
                "camera": privacy.camera_users()}

    @Slot()
    def openPermissions(self):
        privacy.open_permissions()

    # --- Ноутбук -----------------------------------------------------------------------------------------
    @Slot(result="QVariantMap")
    def laptopInfo(self):
        return {"batteries": power.batteries(), "profile": power.profile(),
                "profiles": [p for p in power.PROFILES if p["id"] in power.profiles_available()],
                "brightness": power.brightness()}

    @Slot(str)
    def setProfile(self, pid):
        power.set_profile(pid)
        self.changed.emit("laptop")

    @Slot(int)
    def setBrightness(self, pct):
        power.set_brightness(pct)

    @Slot(int)
    def setChargeLimit(self, value):
        def work(report):
            self._ok(power.set_charge_limit(value))
            self.changed.emit("laptop")
            return "Без ограничения" if value >= 100 else f"Батарея будет заряжаться до {value}%"
        self._run("charge", work)

    # --- Помощник ------------------------------------------------------------------------------------------
    @Slot(result="QVariantMap")
    def assistantInfo(self):
        key = assistant.api_key()
        return {"hasKey": bool(key), "keyHint": ("…" + key[-4:]) if len(key) > 8 else "",
                "sdk": assistant.sdk_available(), "model": assistant.MODEL}

    @Slot(str)
    def setApiKey(self, key):
        assistant.set_api_key(key)
        self.changed.emit("assistant")

    @Slot(str)
    def chat(self, text):
        def work():
            try:
                reply = self._chat.send(text)
            except Exception as e:  # noqa: BLE001
                reply = {"text": "", "buttons": [], "error": str(e)}
            self.chatReply.emit(reply)
        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def chatReset(self):
        self._chat.reset()

    @Slot(str, str)
    def runButton(self, kind, target):
        if kind == "quick_action":
            spawn("astramars-actions", *(["--run", target] if target else []))
        elif kind == "settings_page":
            self.openPage.emit(target)
        elif kind == "store_search":
            spawn("astramars-store", "--search", target)
