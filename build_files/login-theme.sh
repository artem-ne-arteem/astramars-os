#!/usr/bin/bash
# Оформление экрана входа (Plasma Login Manager) и экрана блокировки AstraMars:
# точечный стиль (шрифт Doto) + «стекло» как в iOS.
#
# Экран входа собран внутрь программы, но берёт часы, поле пароля и кнопки
# из QML-модуля org.kde.breeze.components. Мы не трогаем системные файлы,
# а кладём свою копию модуля в отдельную папку и подставляем её через
# QML2_IMPORT_PATH. Копия сделана для Plasma 6.8 — на другой версии подмена
# не включается, и экран входа остаётся стандартным (вход не сломается).
set -ouex pipefail

TESTED_PLASMA="6.8."
SRC=/usr/share/astramars/login-theme/breeze-components
OVL_ROOT=/usr/share/astramars/login-theme/qml
OVL="$OVL_ROOT/org/kde/breeze/components"
SYS=/usr/lib64/qt6/qml/org/kde/breeze/components
ENV_FILES=(
    /usr/lib/systemd/system/plasmalogin.service.d/50-astramars-login-theme.conf
    /usr/lib/environment.d/50-astramars-login-theme.conf
)

### Шрифт Doto (точечный, лицензия OFL)
# Закреплён на версии из репозитория Google Fonts и проверяется по sha256
DOTO_BASE="https://raw.githubusercontent.com/google/fonts/2c982e6bdf88fefbe9e34e78695d8e9e02d788ec/ofl/doto"
mkdir -p /usr/share/fonts/doto
fetch() {  # fetch URL FILE SHA256 — с повторами, пока не совпадёт контрольная сумма
    for attempt in 1 2 3 4 5; do
        if curl -fsSL --retry 3 -o "$2" "$1" && echo "$3  $2" | sha256sum -c -; then
            return 0
        fi
        echo "попытка $attempt: файл не скачался или повреждён, повторяю"
        sleep $((attempt * 5))
    done
    return 1
}
fetch "$DOTO_BASE/Doto%5BROND,wght%5D.ttf" /usr/share/fonts/doto/Doto.ttf \
    6f4fe7d37853b91df3698daa84cde2dbe1c9695d88c986e6510134910337d426
fetch "$DOTO_BASE/OFL.txt" /usr/share/fonts/doto/OFL.txt \
    26a7b58bdba6cda8a78ca6e8b3791d8013b8abc6d5e6519f84193893aee02020
fc-cache -f /usr/share/fonts/doto
fc-list | grep -i doto

### Подмена компонентов Breeze
disable_theme() {
    echo "ВНИМАНИЕ: $1 — экран входа остаётся стандартным"
    rm -f "${ENV_FILES[@]}"
    rm -rf "$OVL_ROOT"
    exit 0
}

PLASMA_VERSION="$(rpm -q --qf '%{VERSION}' plasma-workspace)"
[[ "$PLASMA_VERSION" == ${TESTED_PLASMA}* ]] || disable_theme "Plasma $PLASMA_VERSION не проверена с темой входа AstraMars"
[ -f "$SYS/qmldir" ] || disable_theme "нет модуля $SYS"

# Наши правки сделаны поверх конкретных версий файлов. Если KDE их поменял —
# не подменяем, чтобы не потерять их исправления.
(cd "$SYS" && sha256sum -c /usr/share/astramars/login-theme/upstream-6.8.2.sha256) \
    || disable_theme "системные компоненты Breeze отличаются от тех, на которых сделана тема"

ls -la "$SYS"
cat "$SYS/qmldir"

mkdir -p "$OVL"
# Системный модуль целиком: неизменённые QML — копии, плагин и описание типов — ссылки
for f in "$SYS"/*; do
    case "$(basename "$f")" in
        qmldir) ;;
        *.qml) cp -a "$f" "$OVL/" ;;
        *) ln -sf "$f" "$OVL/" ;;
    esac
done
# Поверх — наши часы, подложка пароля и кнопки
cp -a "$SRC/." "$OVL/"
# Без строки prefer движок берёт QML-файлы с диска (наши), а не вшитые в плагин
grep -v '^prefer ' "$SYS/qmldir" > "$OVL/qmldir"
cat "$OVL/qmldir"

# Все QML-файлы, перечисленные в qmldir, должны быть у нас
missing=0
while read -r name version file; do
    case "$file" in
        *.qml) [ -f "$OVL/$file" ] || { echo "нет файла $file"; missing=1; } ;;
    esac
done < "$OVL/qmldir"
[ "$missing" = 0 ]

### Проверка: модуль загружается с нашими компонентами и без ошибок
TEST=/tmp/login-theme-test
mkdir -p "$TEST"
cat > "$TEST/test.qml" <<'QML'
import QtQuick
import org.kde.breeze.components as BC

Item {
    width: 1280; height: 800
    BC.Clock { id: clock }
    BC.ActionButton { icon.name: "system-reboot"; text: "Перезагрузка" }
    BC.SessionManagementScreen {
        anchors.fill: parent
        userListModel: ListModel { ListElement { name: "astra"; realName: "Astra"; icon: ""; needsPassword: true } }
        actionItems: [
            BC.ActionButton { icon.name: "system-suspend"; text: "Сон" },
            BC.ActionButton { icon.name: "system-shutdown"; text: "Выключение" }
        ]
        Item { implicitHeight: 30 }
    }
    BC.RejectPasswordAnimation { target: clock }
    // Python читает это свойство: если подмена сработала, у часов есть dotFont = "Doto"
    property string overlayCheck: clock.dotFont === "Doto" ? "OVERLAY_OK" : "OVERLAY_NOT_USED"
}
QML
# Отдельной программы qml в образе нет — грузим через PySide6 (те же системные Qt и модули)
cat > "$TEST/run.py" <<'PY'
import sys
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
app = QGuiApplication(sys.argv)
view = QQuickView()
view.engine().warnings.connect(lambda ws: [print("QML warning:", w.toString(), flush=True) for w in ws])
view.setSource(QUrl.fromLocalFile(sys.argv[1]))
for e in view.errors():
    print("QML Error:", e.toString(), flush=True)
if view.status() != QQuickView.Status.Ready:
    print("QML Error: test scene did not load", flush=True)
    sys.exit(1)
view.show()
from PySide6.QtCore import QTimer
def finish():
    print("ASTRAMARS_LOGIN_THEME", view.rootObject().property("overlayCheck"), flush=True)
    app.quit()
QTimer.singleShot(2000, finish)
app.exec()
PY
QML2_IMPORT_PATH="$OVL_ROOT" QML_IMPORT_PATH="$OVL_ROOT" QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    timeout 60 python3 "$TEST/run.py" "$TEST/test.qml" > "$TEST/log.txt" 2>&1 || true
cat "$TEST/log.txt"
grep -q "ASTRAMARS_LOGIN_THEME OVERLAY_OK" "$TEST/log.txt"
if grep -E "Error|is not a type|not installed|is not available|Cannot assign|ReferenceError|TypeError" "$TEST/log.txt" \
        | grep -v -E "Kirigami|kirigami.*style|libEGL|MESA|dbus|D-Bus|org.kde.plasma.private.battery|XDG_RUNTIME_DIR"; then
    echo "Тема экрана входа загружается с ошибками — останавливаю сборку"
    exit 1
fi
rm -rf "$TEST"
echo "Тема экрана входа AstraMars включена для Plasma $PLASMA_VERSION"
