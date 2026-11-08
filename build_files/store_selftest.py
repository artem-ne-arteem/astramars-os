"""Самотест AstraMars Store на свежем каталоге Flathub.

python3 store_selftest.py /usr/lib/astramars-store /tmp/store-check   (в папке лежит appstream.xml.gz)
Ломает сборку, только если каталог не читается. Пропавшие из Flathub приложения подборки —
предупреждение: магазин их просто не покажет.
"""

import os
import sys

sys.path.insert(0, sys.argv[1])
os.environ["ASTRAMARS_STORE_APPSTREAM"] = sys.argv[2]
from astramars_store import catalog  # noqa: E402

apps = catalog.load_catalog()
print(f"Flathub: {len(apps)} приложений")
assert len(apps) > 1000, "каталог Flathub не прочитался"

curated = [i for _, _, ids in catalog.CURATED for i in ids] + catalog.FEATURED
missing = sorted({i for i in curated if i not in apps})
if missing:
    print("ПРЕДУПРЕЖДЕНИЕ: этих приложений подборки нет во Flathub:", ", ".join(missing))
print(f"подборка: {len(set(curated)) - len(missing)} из {len(set(curated))} найдено")

telegram = apps.get("org.telegram.desktop")
assert telegram and telegram["name"], "Telegram не найден — что-то не так с разбором"
for q in ("telegram", "фото", "minecraft"):
    found = [a["name"] for a in catalog.search(apps, q)[:4]]
    print(f"поиск «{q}»:", found)
    assert found, f"поиск «{q}» ничего не нашёл"
print("Самотест магазина пройден")
