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
mkdir -p /usr/share/fonts/doto
curl -fsSL --retry 3 -o /usr/share/fonts/doto/Doto.ttf \
    "https://github.com/google/fonts/raw/main/ofl/doto/Doto%5BROND,wght%5D.ttf"
curl -fsSL --retry 3 -o /usr/share/fonts/doto/OFL.txt \
    "https://github.com/google/fonts/raw/main/ofl/doto/OFL.txt"
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
        Item { implicitHeight: 30 }
    }
    BC.RejectPasswordAnimation { target: clock }
    Timer {
        interval: 1500; running: true
        onTriggered: {
            console.log("ASTRAMARS_LOGIN_THEME", clock.dotFont === "Doto" ? "OVERLAY_OK" : "OVERLAY_NOT_USED")
            Qt.quit()
        }
    }
}
QML
QML_BIN="$(command -v qml || ls /usr/lib64/qt6/bin/qml)"
QML2_IMPORT_PATH="$OVL_ROOT" QML_IMPORT_PATH="$OVL_ROOT" QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    timeout 60 "$QML_BIN" "$TEST/test.qml" > "$TEST/log.txt" 2>&1 || true
cat "$TEST/log.txt"
grep -q "ASTRAMARS_LOGIN_THEME OVERLAY_OK" "$TEST/log.txt"
if grep -E "Error|is not a type|not installed|is not available|Cannot assign|ReferenceError|TypeError" "$TEST/log.txt" \
        | grep -v "Kirigami\|kirigami.*style\|libEGL\|MESA\|dbus\|D-Bus\|org.kde.plasma.private.battery"; then
    echo "Тема экрана входа загружается с ошибками — останавливаю сборку"
    exit 1
fi
rm -rf "$TEST"
echo "Тема экрана входа AstraMars включена для Plasma $PLASMA_VERSION"
