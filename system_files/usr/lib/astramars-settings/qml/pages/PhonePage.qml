import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "PHONE"
    caption: "Уведомления с телефона на компьютере, файлы туда и обратно, общий буфер обмена и SMS — через KDE Connect."

    property var p: backend.phoneInfo()
    property string shareTo: ""
    Connections {
        target: backend
        function onChanged(what) { if (what === "phone") root.p = backend.phoneInfo() }
    }
    Timer { interval: 4000; repeat: true; running: true; onTriggered: root.p = backend.phoneInfo() }

    FileDialog {
        id: fileDialog
        title: "Что отправить на телефон"
        onAccepted: backend.phoneShare(root.shareTo, selectedFile.toString())
    }

    Card {
        title: "Устройства рядом"
        subtitle: !root.p.installed ? "KDE Connect не установлен" :
                  root.p.devices.length ? "Телефон и компьютер должны быть в одной сети Wi-Fi"
                                        : "Пока никого. Установите KDE Connect на телефон и подключитесь к той же сети Wi-Fi."
        Repeater {
            model: root.p.devices
            Rectangle {
                id: dev
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: 64
                radius: 16
                color: Theme.surface2
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 12
                    spacing: 12
                    Rectangle {
                        width: 38; height: 38; radius: 12
                        color: Theme.glass
                        Rectangle { anchors.centerIn: parent; width: 14; height: 22; radius: 4; color: "transparent"
                                    border.width: 2; border.color: Theme.fg }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text { text: dev.modelData.name; color: Theme.fg; font.pixelSize: 15; font.weight: Font.DemiBold }
                        RowLayout {
                            spacing: 6
                            StatusDot { kind: dev.modelData.reachable ? "ok" : "" }
                            Text {
                                text: (dev.modelData.paired ? "подключён" : "не подключён") + (dev.modelData.reachable ? " · рядом" : " · не в сети")
                                color: Theme.muted; font.pixelSize: 12
                            }
                        }
                    }
                    Btn { visible: !dev.modelData.paired; text: "Подключить"; primary: true; small: true
                          onClicked: backend.phoneAction("pair", dev.modelData.id) }
                    Btn { visible: dev.modelData.paired && dev.modelData.reachable; text: "Отправить файл"; small: true
                          onClicked: { root.shareTo = dev.modelData.id; fileDialog.open() } }
                    Btn { visible: dev.modelData.paired && dev.modelData.reachable; text: "Найти телефон"; small: true
                          onClicked: backend.phoneAction("ring", dev.modelData.id) }
                    Btn { visible: dev.modelData.paired; text: "Отключить"; small: true; danger: true
                          onClicked: backend.phoneAction("unpair", dev.modelData.id) }
                }
            }
        }
        RowLayout {
            spacing: 10
            Btn { text: "Искать снова"; small: true; busy: app.running("phone"); onClicked: backend.phoneAction("refresh", "") }
            Btn { text: "Открыть KDE Connect"; small: true; onClicked: backend.openKdeConnect() }
            Btn { text: "Что синхронизировать…"; small: true; onClicked: backend.openKde("kcm_kdeconnect") }
        }
    }

    Card {
        title: "Как подключить телефон"
        RowLayout {
            spacing: 24
            Rectangle {
                Layout.preferredWidth: 168
                Layout.preferredHeight: 168
                radius: 18
                color: "#ffffff"
                visible: root.p.qr !== ""
                Image { anchors.fill: parent; anchors.margins: 10; source: root.p.qr; sourceSize: Qt.size(300, 300); smooth: false }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10
                Repeater {
                    model: [
                        "Наведите камеру Android-телефона на QR-код и установите KDE Connect из Google Play (или F-Droid).",
                        "Подключите телефон к той же сети Wi-Fi, что и компьютер.",
                        "Нажмите «Подключить» здесь и подтвердите на телефоне.",
                        "На iPhone тоже есть KDE Connect в App Store: файлы и буфер обмена работают, SMS — нет."
                    ]
                    RowLayout {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        spacing: 12
                        Text { text: "0" + (index + 1); color: Theme.accent; font.family: Theme.dots; font.pixelSize: 18; font.weight: Font.Black }
                        Text { text: modelData; color: Theme.fg; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                }
            }
        }
    }
}
