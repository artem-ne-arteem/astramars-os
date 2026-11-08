import QtQuick
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "SYSTEM"
    caption: "Обновления без риска: если новая версия не понравится, вернитесь к прошлой одной кнопкой."

    property var upd: backend.updateStatus()
    property var snaps: backend.snapshotsInfo()
    property bool confirmRollback: false
    property string confirmDelete: ""
    readonly property bool busyUpdate: upd.phase === "checking" || upd.phase === "downloading"

    Timer { interval: 1500; repeat: true; running: true; onTriggered: root.upd = backend.updateStatus() }
    Connections {
        target: backend
        function onChanged(what) { if (what === "snapshots") root.snaps = backend.snapshotsInfo() }
    }

    // --- Обновления ---------------------------------------------------------------------------------
    Card {
        title: "Обновление системы"
        subtitle: root.upd.phase === "checking" ? "Проверяю…"
                : root.upd.phase === "downloading" ? (root.upd.line || "Скачиваю…")
                : root.upd.staged ? "Новая версия скачана — включится после перезагрузки"
                : root.upd.available ? "Доступна новая версия " + (root.upd.available.version || "")
                : root.upd.error ? "Не удалось проверить: " + root.upd.error
                : "Установлена последняя версия" + (root.upd.booted && root.upd.booted.version ? " · " + root.upd.booted.version : "")
        badge: root.upd.available ? "новое" : ""
        DotProgress { visible: root.busyUpdate; text: "" }
        RowLayout {
            spacing: 10
            Btn {
                visible: !root.upd.staged
                text: root.upd.available ? "Скачать обновление" : "Проверить"
                primary: !!root.upd.available
                busy: root.busyUpdate
                onClicked: root.upd.available ? backend.applyUpdate() : backend.checkUpdates()
            }
            Btn { visible: !!root.upd.staged; text: "Перезагрузить"; primary: true; onClicked: backend.reboot() }
            Btn { text: "Программы…"; onClicked: backend.storeSearch("") }
        }
    }

    // --- Откат --------------------------------------------------------------------------------------------
    Card {
        title: "Вернуть прошлую версию"
        subtitle: "AstraMars хранит предыдущую версию системы целиком. Файлы и программы при откате не трогаются."
        RowLayout {
            spacing: 10
            Btn {
                visible: !root.confirmRollback
                text: "Откатить…"
                onClicked: root.confirmRollback = true
            }
            Text { visible: root.confirmRollback; text: "После перезагрузки включится прошлая версия. Продолжить?"
                   color: Theme.fg; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Btn { visible: root.confirmRollback; text: "Да, откатить"; danger: true; busy: app.running("rollback")
                  onClicked: { backend.rollback(); root.confirmRollback = false } }
            Btn { visible: root.confirmRollback; text: "Отмена"; small: true; onClicked: root.confirmRollback = false }
        }
    }

    // --- Машина времени -------------------------------------------------------------------------------
    Card {
        title: "Машина времени"
        subtitle: root.snaps.available
                  ? "Снимки домашних папок: удалили или испортили файл — откройте снимок и заберите прошлую версию. Снимок почти не занимает места."
                  : "Недоступно: " + root.snaps.reason
        badge: root.snaps.available ? root.snaps.list.length + " снимков" : ""

        SettingRow {
            visible: root.snaps.available
            title: "Снимок каждый день"
            subtitle: "Хранятся последние 7 ежедневных снимков, ручные — пока не удалите"
            Toggle { checked: root.snaps.timer; onToggled: function (v) { backend.setSnapshotTimer(v) } }
        }

        Repeater {
            model: root.snaps.list
            Rectangle {
                id: snap
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: 52
                radius: 14
                color: Theme.surface2
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 10
                    spacing: 12
                    StatusDot { kind: snap.modelData.auto ? "" : "accent" }
                    Text { text: snap.modelData.date; color: Theme.fg; font.pixelSize: 14; Layout.fillWidth: true }
                    Text { text: snap.modelData.auto ? "ежедневный" : "вручную"; color: Theme.muted; font.pixelSize: 12 }
                    Btn { text: "Открыть"; small: true; onClicked: backend.openSnapshot(snap.modelData.name) }
                    Btn {
                        text: root.confirmDelete === snap.modelData.name ? "Точно удалить" : "Удалить"
                        small: true; danger: true
                        onClicked: {
                            if (root.confirmDelete === snap.modelData.name) { backend.deleteSnapshot(snap.modelData.name); root.confirmDelete = "" }
                            else root.confirmDelete = snap.modelData.name
                        }
                    }
                }
            }
        }
        Btn { visible: root.snaps.available; text: "Сделать снимок сейчас"; primary: true; busy: app.running("snapshot")
              onClicked: backend.createSnapshot() }
    }

    Card {
        title: "Ещё"
        RowLayout {
            spacing: 10
            Btn { text: "Быстрые действия"; onClicked: backend.runButton("quick_action", "") }
            Btn { text: "Автозапуск…"; onClicked: backend.openKde("kcm_autostart") }
            Btn { text: "Пользователи…"; onClicked: backend.openKde("kcm_users") }
        }
    }
}
