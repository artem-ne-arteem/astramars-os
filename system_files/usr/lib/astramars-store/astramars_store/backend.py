"""Связка интерфейса магазина с каталогом и flatpak."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, QObject, Qt, QTimer, Signal, Slot

from . import catalog, flatpak, updates

POPULAR = "popular"
INSTALLED = "installed"
UPDATES = "updates"
SEARCH = "search"


ROLES = ["appId", "name", "summary", "icon", "developer", "status", "progress", "detail"]


class AppModel(QAbstractListModel):
    """Список карточек: при смене раздела — сброс, при прогрессе установки — только одна строка."""

    def __init__(self):
        super().__init__()
        self._rows = []

    def roleNames(self):
        return {Qt.UserRole + i: name.encode() for i, name in enumerate(ROLES)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        return self._rows[index.row()].get(ROLES[role - Qt.UserRole])

    def set_rows(self, rows):
        if [r["appId"] for r in rows] == [r["appId"] for r in self._rows]:
            for i, row in enumerate(rows):
                self.update_row(i, row)
            return
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def update_row(self, i, row):
        if self._rows[i] != row:
            self._rows[i] = row
            self.dataChanged.emit(self.index(i), self.index(i))

    def update_app(self, row):
        for i, old in enumerate(self._rows):
            if old["appId"] == row["appId"]:
                self.update_row(i, row)


class Backend(QObject):
    itemsChanged = Signal()
    categoryChanged = Signal()
    loadingChanged = Signal()
    toast = Signal(str)

    _catalogLoaded = Signal(object, object)
    _jobProgress = Signal(str, int, str)   # id, процент, скорость
    _jobDone = Signal(str, str, str)  # id, action, error
    _appUpdatesFound = Signal(object)
    _systemRead = Signal(object, str)

    systemChanged = Signal()
    updatesChanged = Signal()

    def __init__(self, fp=None):
        super().__init__()
        self._fp = fp or flatpak.create()
        self._apps = {}
        self._installed = set()
        self._jobs = {}       # id → {"action": install|remove, "progress": int, "queued": bool}
        self._category = POPULAR
        self._query = ""
        self._loading = True
        self._model = AppModel()
        self._io = ThreadPoolExecutor(max_workers=2)
        self._queue = ThreadPoolExecutor(max_workers=1)   # установки по одной
        self._sys = updates.create()
        self._app_updates = set()
        self._system = updates.summarize({}, "")
        self._ticks = 0
        self._appUpdatesFound.connect(self._on_app_updates)
        self._systemRead.connect(self._on_system)
        self._sys_timer = QTimer(self, interval=1500, timeout=self._poll_system)
        self._sys_timer.start()
        self._catalogLoaded.connect(self._on_catalog)
        self._jobProgress.connect(self._on_progress)
        self._jobDone.connect(self._on_done)

    def start(self):
        def work():
            self._fp.ensure_flathub()
            self._catalogLoaded.emit(catalog.load_catalog(), self._fp.installed())
            self._appUpdatesFound.emit(self._fp.updates())
            self._fp.refresh_appstream()        # свежий список — может занять время
            self._catalogLoaded.emit(catalog.load_catalog(), self._fp.installed())
        self._io.submit(work)
        self._start_system("check", quiet=True)
        self._poll_system(force=True)

    def shutdown(self):
        self._sys_timer.stop()
        self._io.shutdown(wait=False, cancel_futures=True)
        self._queue.shutdown(wait=False, cancel_futures=True)

    # --- свойства --------------------------------------------------------------------

    @Property("QVariantList", notify=updatesChanged)
    def categories(self):
        count = self.updatesCount
        chips = [{"key": POPULAR, "title": "Популярное"},
                 {"key": UPDATES, "title": f"Обновления · {count}" if count else "Обновления"}]
        chips += [{"key": key, "title": title} for key, title, _ in catalog.CURATED]
        chips.append({"key": INSTALLED, "title": "Установленные"})
        return chips

    @Property(int, notify=updatesChanged)
    def updatesCount(self):
        system = 1 if self._system.get("state") in ("available", "ready") else 0
        return len(self._app_updates) + system

    @Property(int, notify=updatesChanged)
    def appUpdatesCount(self):
        return len(self._app_updates)

    @Property("QVariantMap", notify=systemChanged)
    def system(self):
        return dict(self._system)

    @Property(str, notify=categoryChanged)
    def category(self):
        return SEARCH if self._query.strip() else self._category

    @Property(str, notify=categoryChanged)
    def title(self):
        if self._query.strip():
            return "Поиск"
        if self._category == UPDATES:
            return "Обновления"
        return next((c["title"] for c in self.categories if c["key"] == self._category), "")

    @Property(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    @Property(int, notify=itemsChanged)
    def catalogSize(self):
        return len(self._apps)

    @Property(QObject, constant=True)
    def model(self):
        return self._model

    @Property(int, notify=itemsChanged)
    def count(self):
        return self._model.rowCount()

    def _refresh(self):
        self._model.set_rows([self._item(app_id) for app_id in self._visible_ids()])
        self.itemsChanged.emit()

    # --- действия --------------------------------------------------------------------

    @Slot(str)
    def setCategory(self, key):
        self._category = key
        self._query = ""
        self.categoryChanged.emit()
        self._refresh()

    @Slot(str)
    def setQuery(self, text):
        self._query = text
        self.categoryChanged.emit()
        self._refresh()

    @Slot(str)
    def install(self, app_id):
        self._enqueue(app_id, "install")

    @Slot(str)
    def remove(self, app_id):
        self._enqueue(app_id, "remove")

    @Slot(str)
    def updateApp(self, app_id):
        self._enqueue(app_id, "update")

    @Slot()
    def checkUpdates(self):
        self._start_system("check")
        self._io.submit(lambda: self._appUpdatesFound.emit(self._fp.updates()))

    @Slot()
    def updateSystem(self):
        self._start_system("apply")

    @Slot()
    def updateAll(self):
        if self._system.get("state") in ("available", "current", "unknown", "error"):
            self._start_system("apply", quiet=True)
        for app_id in sorted(self._app_updates):
            self._enqueue(app_id, "update")
        if not self._app_updates and self._system.get("state") == "ready":
            self.toast.emit("Всё уже скачано — осталось перезагрузить компьютер")

    @Slot()
    def rebootNow(self):
        self._sys.reboot()

    @Slot(str)
    def launch(self, app_id):
        self._fp.launch(app_id)
        self.toast.emit(f"Запускаю «{self._name(app_id)}»")

    # --- внутреннее ------------------------------------------------------------------

    def _name(self, app_id):
        return (self._apps.get(app_id) or {}).get("name") or app_id

    def _visible_ids(self):
        if self._query.strip():
            return [a["id"] for a in catalog.search(self._apps, self._query)]
        if self._category == UPDATES:
            return sorted(self._app_updates | {i for i, j in self._jobs.items() if j["action"] == "update"},
                          key=lambda i: self._name(i).lower())
        if self._category == INSTALLED:
            ids = sorted(self._installed | {i for i, j in self._jobs.items() if j["action"] == "install"},
                         key=lambda i: self._name(i).lower())
            return ids
        if self._category == POPULAR:
            ids = list(catalog.FEATURED)
            for _, _, section in catalog.CURATED:
                ids += section[:2]
            seen, result = set(), []
            for i in ids:
                if i not in seen:
                    seen.add(i)
                    result.append(i)
            return [i for i in result if i in self._apps or not self._apps]
        for key, _, section in catalog.CURATED:
            if key == self._category:
                return [i for i in section if i in self._apps or not self._apps]
        return []

    def _item(self, app_id):
        app = self._apps.get(app_id) or {"name": app_id, "summary": "", "icon": "", "developer": ""}
        job = self._jobs.get(app_id)
        if job:
            state = "queued" if job["queued"] else {"install": "installing", "remove": "removing",
                                                    "update": "updating"}[job["action"]]
        elif app_id in self._app_updates:
            state = "update"
        else:
            state = "installed" if app_id in self._installed else "available"
        return {
            "appId": app_id,
            "name": app["name"],
            "summary": app["summary"],
            "icon": app["icon"],
            "developer": app["developer"],
            "status": state,
            "progress": job["progress"] if job else 0,
            "detail": job.get("detail", "") if job else "",
        }

    def _enqueue(self, app_id, action):
        if app_id in self._jobs:
            return
        self._jobs[app_id] = {"action": action, "progress": 0, "queued": True}
        self._model.update_app(self._item(app_id))

        def work():
            self._jobProgress.emit(app_id, 0, "")
            try:
                fn = {"install": self._fp.install, "remove": self._fp.uninstall, "update": self._fp.update}[action]
                fn(app_id, lambda p, detail="": self._jobProgress.emit(app_id, p, detail))
                self._jobDone.emit(app_id, action, "")
            except flatpak.FlatpakError as e:
                self._jobDone.emit(app_id, action, str(e))
            except OSError as e:
                self._jobDone.emit(app_id, action, f"не удалось запустить flatpak: {e}")
        self._queue.submit(work)

    def _on_catalog(self, apps, installed):
        if apps:
            self._apps = apps
        self._installed = installed
        if self._loading:
            self._loading = False
            self.loadingChanged.emit()
        self._refresh()

    def _on_progress(self, app_id, value, detail):
        job = self._jobs.get(app_id)
        if job:
            job["queued"] = False
            job["progress"] = value
            job["detail"] = detail
            self._model.update_app(self._item(app_id))

    def _on_done(self, app_id, action, error):
        self._jobs.pop(app_id, None)
        name = self._name(app_id)
        if error:
            self.toast.emit(f"«{name}»: {error}")
        elif action == "install":
            self._installed.add(app_id)
            self.toast.emit(f"«{name}» установлено — ищите в меню")
        elif action == "update":
            self._app_updates.discard(app_id)
            self.updatesChanged.emit()
            self.toast.emit(f"«{name}» обновлено")
        else:
            self._installed.discard(app_id)
            self.toast.emit(f"«{name}» удалено")
        if self._category in (INSTALLED, UPDATES) and not self._query.strip():
            self._refresh()
        else:
            self._model.update_app(self._item(app_id))

    # --- обновления системы и приложений ------------------------------------------------

    def _start_system(self, kind, quiet=False):
        try:
            self._sys.start(kind)
            if kind == "apply" and not quiet:
                self.toast.emit("Скачиваю обновление системы — можно продолжать работать")
            self._poll_system(force=True)
        except (updates.UpdateError, OSError) as e:
            if not quiet:
                self.toast.emit(f"Обновление системы: {e}")

    def _poll_system(self, force=False):
        self._ticks += 1
        busy = self._system.get("state") in ("checking", "downloading")
        if not (force or busy or self._category == UPDATES or self._ticks % 20 == 0):
            return
        self._io.submit(lambda: self._systemRead.emit(self._sys.read(), self._sys.running()))

    def _on_system(self, raw, running):
        info = updates.summarize(raw, running)
        was = self._system.get("state")
        if info != self._system:
            self._system = info
            self.systemChanged.emit()
            self.updatesChanged.emit()
        if was == "downloading" and info["state"] == "ready":
            self.toast.emit("Обновление системы скачано — перезагрузите компьютер")
        elif was == "downloading" and info["state"] == "error":
            self.toast.emit("Обновление системы не скачалось: " + info["error"].splitlines()[-1][:120])

    def _on_app_updates(self, found):
        self._app_updates = set(found)
        self.updatesChanged.emit()
        if self._category == UPDATES and not self._query.strip():
            self._refresh()
        else:
            for app_id in found:
                self._model.update_app(self._item(app_id))
