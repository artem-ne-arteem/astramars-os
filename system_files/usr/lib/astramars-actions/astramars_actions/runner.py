"""Выполнение сценария по шагам.

Шаги пользователя — `bash -lc`, шаги администратора — `pkexec bash -c` (KDE спросит пароль).
"""

import os
import shutil
import subprocess
import time

STEP_TIMEOUT = 15 * 60


def free_bytes(path=None):
    try:
        return shutil.disk_usage(path or os.path.expanduser("~")).free
    except OSError:
        return 0


def human_bytes(n):
    for unit, size in (("ГБ", 1 << 30), ("МБ", 1 << 20), ("КБ", 1 << 10)):
        if abs(n) >= size:
            return f"{n / size:.1f} {unit}".replace(".", ",")
    return f"{int(n)} Б"


class Runner:
    def run_step(self, step):
        """(успех, вывод) для одного шага."""
        # pipefail: ошибка в начале цепочки «a | b» не должна прятаться за успехом последней команды
        script = "set -o pipefail; " + step["run"]
        cmd = ["pkexec", "/usr/bin/bash", "-c", script] if step.get("root") else ["bash", "-lc", script]
        try:
            p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               timeout=STEP_TIMEOUT, env=dict(os.environ, LC_NUMERIC="C"))
        except subprocess.TimeoutExpired:
            return False, "шаг не закончился за 15 минут"
        except FileNotFoundError as e:
            return False, f"не найдена программа: {e.filename}"
        out = (p.stdout + p.stderr).strip()
        if step.get("root") and p.returncode in (126, 127) and not out:
            out = "нужен пароль администратора — вход отменён"
        return p.returncode == 0, out


class FakeRunner:
    """Режим разработки: шаги «выполняются» за полсекунды."""

    DEMO = {
        "Задержка до 1.1.1.1": "Задержка: 18 мс",
        "Проверяю DNS": "DNS: работает",
        "Скорость скачивания": "Скорость: 94,6 Мбит/с",
    }

    def run_step(self, step):
        time.sleep(0.6)
        if "fail" in step["run"]:
            return False, "команда завершилась с ошибкой"
        return True, self.DEMO.get(step["title"], f"$ {step['run'][:60]}")


def create():
    return FakeRunner() if os.environ.get("ASTRAMARS_ACTIONS_DEV") else Runner()
