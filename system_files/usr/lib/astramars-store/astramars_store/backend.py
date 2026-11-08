"""Связка интерфейса магазина с каталогом и flatpak."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, QObject, Qt, Signal, Slot

from . import catalog, flatpak

POPULAR = "popular"
INSTALLED = "installed"
SEARCH = "search"


ROLES = ["appId", "name", "summary", "icon", "developer", "status", "progress"]


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
    _jobProgress = Signal(str, int)
    _jobDone = Signal(str, str, str)  # id, action, error

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
        self._catalogLoaded.connect(self._on_catalog)
        self._jobProgress.connect(self._on_progress)
        self._jobDone.connect(self._on_done)

    def start(self):
        def work():
            self._fp.ensure_flathub()
            self._catalogLoaded.emit(catalog.load_catalog(), self._fp.installed())
            self._fp.refresh_appstream()        # свежий список — может занять время
            self._catalogLoaded.emit(catalog.load_catalog(), self._fp.installed())
        self._io.submit(work)

    def shutdown(self):
        self._io.shutdown(wait=False, cancel_futures=True)
        self._queue.shutdown(wait=False, cancel_futures=True)

    # --- свойства --------------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def categories(self):
        chips = [{"key": POPULAR, "title": "Популярное"}]
        chips += [{"key": key, "title": title} for key, title, _ in catalog.CURATED]
        chips.append({"key": INSTALLED, "title": "Установленные"})
        return chips

    @Property(str, notify=categoryChanged)
    def category(self):
        return SEARCH if self._query.strip() else self._category

    @Property(str, notify=categoryChanged)
    def title(self):
        if self._query.strip():
            return "Поиск"
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
    def launch(self, app_id):
        self._fp.launch(app_id)
        self.toast.emit(f"Запускаю «{self._name(app_id)}»")

    # --- внутреннее ------------------------------------------------------------------

    def _name(self, app_id):
        return (self._apps.get(app_id) or {}).get("name") or app_id

    def _visible_ids(self):
        if self._query.strip():
            return [a["id"] for a in catalog.search(self._apps, self._query)]
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
            state = "queued" if job["queued"] else ("installing" if job["action"] == "install" else "removing")
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
        }

    def _enqueue(self, app_id, action):
        if app_id in self._jobs:
            return
        self._jobs[app_id] = {"action": action, "progress": 0, "queued": True}
        self._model.update_app(self._item(app_id))

        def work():
            self._jobProgress.emit(app_id, 0)
            try:
                fn = self._fp.install if action == "install" else self._fp.uninstall
                fn(app_id, lambda p: self._jobProgress.emit(app_id, p))
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

    def _on_progress(self, app_id, value):
        job = self._jobs.get(app_id)
        if job:
            job["queued"] = False
            job["progress"] = value
            self._model.update_app(self._item(app_id))

    def _on_done(self, app_id, action, error):
        self._jobs.pop(app_id, None)
        name = self._name(app_id)
        if error:
            self.toast.emit(f"«{name}»: {error}")
        elif action == "install":
            self._installed.add(app_id)
            self.toast.emit(f"«{name}» установлено — ищите в меню")
        else:
            self._installed.discard(app_id)
            self.toast.emit(f"«{name}» удалено")
        if self._category == INSTALLED and not self._query.strip():
            self._refresh()
        else:
            self._model.update_app(self._item(app_id))
