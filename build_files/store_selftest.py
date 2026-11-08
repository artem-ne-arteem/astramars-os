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

# Разбор вывода bootc в помощнике обновлений (строки — из bootc crates/lib/src/cli.rs)
import importlib.machinery  # noqa: E402
sys.dont_write_bytecode = True  # не оставлять кэш Python в образе
import importlib.util  # noqa: E402

loader = importlib.machinery.SourceFileLoader("astramars_update", "/usr/libexec/astramars-update")
spec = importlib.util.spec_from_loader("astramars_update", loader)
upd = importlib.util.module_from_spec(spec)
loader.exec_module(upd)
ref = "ostree-unverified-registry:ghcr.io/artem-ne-arteem/astramars-os:latest"
assert upd.parse_check(f"No changes in: {ref}\n") is None
found = upd.parse_check(f"Update available for: {ref}\n  Version: 45.1\n  Digest: sha256:abc\n")
assert found == {"version": "45.1", "digest": "sha256:abc"}, found
print("Разбор вывода bootc: OK")
