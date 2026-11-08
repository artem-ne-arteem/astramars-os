#!/usr/bin/bash
# Стиль Plasma «AstraMars» (меню и всплывающие окна): основа — Breeze Dark, сверху наши
# фон окна, подсветка пунктов, шапка/низ меню и вкладки (build_files/make_plasma_theme.py).
set -ouex pipefail

SRC=/usr/share/astramars/plasma-theme
DST=/usr/share/plasma/desktoptheme/astramars
BASE=/usr/share/plasma/desktoptheme/breeze-dark
OURS=(dialogs/background widgets/viewitem widgets/plasmoidheading widgets/tabbar)

ls -la "$BASE" || true
rm -rf "$DST"
mkdir -p "$DST"
if [ -d "$BASE" ]; then
    cp -a "$BASE/." "$DST/"
fi
# Наши элементы должны победить: убираем одноимённые файлы Breeze, в том числе
# варианты для прозрачного (translucent) и непрозрачного (opaque) режима
for name in "${OURS[@]}"; do
    rm -f "$DST/$name.svgz" "$DST/$name.svg" \
          "$DST/translucent/$name.svgz" "$DST/translucent/$name.svg" \
          "$DST/opaque/$name.svgz" "$DST/opaque/$name.svg"
done
cp -a "$SRC/." "$DST/"
rm -f "$DST/metadata.desktop"
find "$DST" -maxdepth 2 | sort

# Проверка: в каждом нашем SVG есть все 9 частей нужных префиксов и отступы
QT_QPA_PLATFORM=offscreen python3 - "$DST" <<'PY'
import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtSvg import QSvgRenderer

app = QGuiApplication(sys.argv[:1])
root = sys.argv[1]
parts = ["topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright"]
need = {
    "dialogs/background.svg": ["", "mask"],
    "widgets/viewitem.svg": ["hover", "selected", "selected+hover"],
    "widgets/plasmoidheading.svg": ["header", "footer"],
    "widgets/tabbar.svg": ["north-active-tab", "south-active-tab"],
}
bad = 0
for path, prefixes in need.items():
    r = QSvgRenderer(f"{root}/{path}")
    assert r.isValid(), f"{path}: SVG не читается"
    for pre in prefixes:
        for part in parts + ([] if pre == "mask" else
                             ["hint-top-margin", "hint-bottom-margin", "hint-left-margin", "hint-right-margin"]):
            el = f"{pre}-{part}" if pre else part
            if not r.elementExists(el):
                print("нет элемента", path, el)
                bad += 1
    corner = r.boundsOnElement(f"{prefixes[0]}-topleft" if prefixes[0] else "topleft")
    print(f"{path}: угол {corner.width():.0f}×{corner.height():.0f}")
sys.exit(1 if bad else 0)
PY

chmod +x /usr/libexec/astramars-menu-setup
command -v gdbus kreadconfig6 plasma-apply-desktoptheme
echo "Стиль Plasma AstraMars собран"
