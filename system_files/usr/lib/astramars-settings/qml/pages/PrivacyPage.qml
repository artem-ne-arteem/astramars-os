import QtQuick
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "PRIVACY"
    caption: "AstraMars ничего о вас не собирает и не отправляет. Здесь видно, кто прямо сейчас слушает и смотрит."

    property var p: backend.privacyInfo()
    Timer { interval: 3000; repeat: true; running: true; onTriggered: root.p = backend.privacyInfo() }

    RowLayout {
        Layout.fillWidth: true
        spacing: 14
        Repeater {
            model: [
                {title: "Микрофон", users: root.p.mic},
                {title: "Камера", users: root.p.camera}
            ]
            Rectangle {
                id: dev
                required property var modelData
                readonly property bool active: modelData.users.length > 0
                Layout.fillWidth: true
                implicitHeight: 128
                radius: 22
                color: active ? Theme.soft(Theme.warn, 0.08) : Theme.surface
                border.width: 1
                border.color: active ? Theme.soft(Theme.warn, 0.5) : Theme.line
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 8
                    RowLayout {
                        StatusDot { kind: dev.active ? "warn" : "ok"; pulse: dev.active }
                        Text { text: dev.modelData.title; color: Theme.muted; font.pixelSize: 13 }
                    }
                    Text { text: dev.active ? "Используется" : "Не используется"; color: Theme.fg; font.pixelSize: 20; font.weight: Font.DemiBold }
                    Text { text: dev.active ? dev.modelData.users.join(", ") : "Никто не записывает"; color: Theme.muted
                           font.pixelSize: 13; elide: Text.ElideRight; Layout.fillWidth: true }
                }
            }
        }
    }

    Card {
        title: "Что система отправляет"
        subtitle: "Мы выключили всё, что в Fedora и KDE могло бы что-то отправлять без спроса"
        Repeater {
            model: root.p.telemetry
            SettingRow {
                required property var modelData
                title: modelData.name
                Text { text: modelData.state; color: modelData.ok ? Theme.ok : Theme.warn; font.pixelSize: 13 }
            }
        }
    }

    Card {
        title: "Разрешения приложений"
        subtitle: "Какие программы видят камеру, микрофон, файлы и сеть. Программы из Магазина работают в «песочнице» и получают только разрешённое."
        RowLayout {
            spacing: 10
            Btn { text: "Разрешения приложений…"; onClicked: backend.openPermissions() }
            Btn { text: "Блокировка экрана…"; onClicked: backend.openKde("kcm_screenlocker") }
        }
    }
}
