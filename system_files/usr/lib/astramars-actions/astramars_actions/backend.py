"""Связка интерфейса «Быстрых действий» со сценариями и исполнителем."""

import time
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from . import actions, runner


class Backend(QObject):
    actionsChanged = Signal()
    toast = Signal(str)

    _stepStarted = Signal(str, int)              # id, номер шага
    _finished = Signal(str, bool, str, object)   # id, успех, итог, журнал

    def __init__(self, run=None):
        super().__init__()
        self._runner = run or runner.create()
        self._custom = actions.load_custom()
        self._state = {}      # id → {"status": running|done|failed, "step": i, "summary": str, "log": [...]}
        self._pool = ThreadPoolExecutor(max_workers=4)
        self._stepStarted.connect(self._on_step)
        self._finished.connect(self._on_finished)

    def shutdown(self):
        self._pool.shutdown(wait=False, cancel_futures=True)

    # --- свойства --------------------------------------------------------------------

    def _all(self):
        return actions.BUILTIN + self._custom

    def _find(self, action_id):
        return next((a for a in self._all() if a["id"] == action_id), None)

    def _view(self, a):
        st = self._state.get(a["id"], {})
        steps = a["steps"]
        i = st.get("step", 0)
        return {
            "id": a["id"],
            "title": a["title"],
            "subtitle": a["subtitle"],
            "icon": a["icon"],
            "custom": bool(a.get("custom")),
            "root": any(s.get("root") for s in steps),
            "confirm": a.get("confirm", ""),
            "steps": len(steps),
            "status": st.get("status", "idle"),
            "step": i,
            "stepTitle": steps[i]["title"] if st.get("status") == "running" and i < len(steps) else "",
            "summary": st.get("summary", ""),
            "hasLog": bool(st.get("log")),
        }

    @Property("QVariantList", notify=actionsChanged)
    def builtins(self):
        return [self._view(a) for a in actions.BUILTIN]

    @Property("QVariantList", notify=actionsChanged)
    def customs(self):
        return [self._view(a) for a in self._custom]

    # --- действия --------------------------------------------------------------------

    @Slot(str)
    def run(self, action_id):
        a = self._find(action_id)
        if not a or self._state.get(action_id, {}).get("status") == "running":
            return
        self._state[action_id] = {"status": "running", "step": 0, "log": []}
        self.actionsChanged.emit()
        self._pool.submit(self._work, a)

    @Slot(str, result="QVariantMap")
    def details(self, action_id):
        a = self._find(action_id) or {}
        st = self._state.get(action_id, {})
        return {"title": a.get("title", ""), "summary": st.get("summary", ""), "status": st.get("status", "idle"),
                "log": "\n\n".join(st.get("log", [])) or "Действие ещё не запускалось"}

    @Slot(str)
    def copyText(self, text):
        QGuiApplication.clipboard().setText(text)
        self.toast.emit("Скопировано")

    @Slot(str, result="QVariantMap")
    def custom(self, action_id):
        a = self._find(action_id) or {}
        return {"id": a.get("id", ""), "title": a.get("title", ""), "commands": a.get("commands", ""),
                "root": bool(a.get("root"))}

    @Slot(str, str, str, bool)
    def saveCustom(self, action_id, title, commands, root):
        item = actions.make_custom(title, commands, root, action_id or None)
        if not item["steps"]:
            self.toast.emit("Добавьте хотя бы одну команду")
            return
        self._custom = [c for c in self._custom if c["id"] != item["id"]]
        self._custom.append(item)
        actions.save_custom(self._custom)
        self.actionsChanged.emit()
        self.toast.emit(f"Действие «{item['title']}» сохранено")

    @Slot(str)
    def deleteCustom(self, action_id):
        self._custom = [c for c in self._custom if c["id"] != action_id]
        self._state.pop(action_id, None)
        actions.save_custom(self._custom)
        self.actionsChanged.emit()

    # --- выполнение ------------------------------------------------------------------

    def _work(self, a):
        log, shown = [], []
        free_before = runner.free_bytes() if a.get("measureSpace") else 0
        started = time.time()
        for i, step in enumerate(a["steps"]):
            self._stepStarted.emit(a["id"], i)
            ok, out = self._runner.run_step(step)
            log.append(f"▸ {step['title']}" + (f"\n{out}" if out else "") + ("" if ok else "\n✗ ошибка"))
            if ok and step.get("show") and out:
                shown.append(out)
            if not ok and not step.get("optional"):
                reason = out.strip().splitlines()[-1] if out.strip() else "команда завершилась с ошибкой"
                self._finished.emit(a["id"], False, f"Шаг «{step['title']}»: {reason[:140]}", log)
                return
        parts = []
        if a.get("measureSpace"):
            freed = runner.free_bytes() - free_before
            parts.append(f"Освобождено {runner.human_bytes(max(0, freed))}")
        if shown:
            parts.append(shown[-1].strip().splitlines()[0][:140] if len(shown) == 1 else
                         " · ".join(s.strip().splitlines()[0][:60] for s in shown[:3]))
        if not parts:
            parts.append(f"Готово за {max(1, round(time.time() - started))} с")
        self._finished.emit(a["id"], True, " · ".join(parts), log)

    def _on_step(self, action_id, i):
        st = self._state.setdefault(action_id, {})
        st.update(status="running", step=i)
        self.actionsChanged.emit()

    def _on_finished(self, action_id, ok, summary, log):
        self._state[action_id] = {"status": "done" if ok else "failed", "step": 0, "summary": summary, "log": log}
        self.actionsChanged.emit()
        a = self._find(action_id) or {"title": ""}
        self.toast.emit(f"«{a['title']}»: {summary}" if ok else f"«{a['title']}» не выполнено — {summary}")
