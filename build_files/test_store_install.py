"""Проверка магазина на настоящей установке с Flathub (запускается в GitHub Actions).

python3 test_store_install.py system_files/usr/lib/astramars-store
Ставит небольшое приложение так же, как кнопка «Установить», и проверяет, что
проценты приходили и росли до 100. Системная установка без прав не пройдёт —
это заодно проверяет запасной вариант «только для пользователя».
"""

import subprocess
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from astramars_store.flatpak import Flatpak  # noqa: E402

APP = sys.argv[2] if len(sys.argv) > 2 else "com.github.tchx84.Flatseal"

events = []
start = time.time()


def on_progress(percent, speed=""):
    events.append((round(time.time() - start, 1), percent, speed))
    print(f"  {events[-1][0]:>6}s  {percent:>3}%  {speed}", flush=True)


fp = Flatpak()
print(f"Устанавливаю {APP}…")
fp.install(APP, on_progress)
print(f"Готово за {time.time() - start:.0f} с, событий прогресса: {len(events)}")

installed = subprocess.run(["flatpak", "list", "--app", "--columns=application"],
                           capture_output=True, text=True).stdout.split()
assert APP in installed, f"{APP} не установилось"

print("Строки прогресса flatpak (первые, середина, последние):")
samples = fp.progress_samples
for line in samples[:4] + samples[len(samples) // 2:len(samples) // 2 + 3] + samples[-3:]:
    print("   ", line)

percents = [p for _, p, _ in events]
assert len(set(percents)) >= 5, f"слишком мало разных процентов: {sorted(set(percents))}"
assert percents == sorted(percents), "проценты уменьшались"
assert percents[-1] >= 99, f"последний процент {percents[-1]}"
assert any(s for _, _, s in events), "скорость ни разу не пришла"
print("Проценты и скорость приходят: OK")

fp.uninstall(APP, lambda p, s="": None)
print("Удаление: OK")
