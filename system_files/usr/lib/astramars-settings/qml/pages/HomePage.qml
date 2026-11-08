import QtQuick
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "ASTRAMARS"
    caption: "В честь кошки Астры и кота Марсика. Ваш компьютер — коротко."

    property var info: backend.info()
    property var upd: backend.updateStatus()
    property var vpn: backend.vpnState()
    property var laptop: backend.laptopInfo()

    // --- Карточка системы с логотипом ---------------------------------------------------------
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 220
        radius: 26
        color: Theme.surface
        border.width: 1
        border.color: Theme.line
        clip: true

        // точечный узор справа
        Grid {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: -10
            columns: 18
            spacing: 12
            opacity: 0.18
            Repeater {
                model: 18 * 10
                Rectangle {
                    required property int index
                    width: 4; height: 4; radius: 2
                    color: (index % 18) > 14 - Math.floor(index / 18) * 0.6 ? Theme.accent : "#ffffff"
                }
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 28
            Image {
                source: logoUrl
                sourceSize: Qt.size(320, 320)
                Layout.preferredWidth: 160
                Layout.preferredHeight: 160
                smooth: true
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Text { text: root.info.name; color: Theme.fg; font.pixelSize: 30; font.weight: Font.Bold }
                RowLayout {
                    spacing: 8
                    Rectangle { width: 8; height: 8; radius: 4; color: Theme.accent }
                    Text {
                        text: "Astra & Mars · " + (root.info.variant === "nvidia" ? "с драйверами NVIDIA" : "основной образ")
                        color: Theme.muted; font.pixelSize: 14
                    }
                }
                Item { Layout.preferredHeight: 8 }
                GridLayout {
                    columns: 2
                    columnSpacing: 22
                    rowSpacing: 6
                    Repeater {
                        model: [
                            ["Компьютер", root.info.host + " · " + root.info.user],
                            ["Процессор", root.info.cpu],
                            ["Видеокарта", root.info.gpu],
                            ["Память", root.info.ram],
                            ["Ядро · Plasma", root.info.kernel + " · " + root.info.plasma],
                            ["Работает", root.info.uptime]
                        ]
                        RowLayout {
                            required property var modelData
                            spacing: 8
                            Layout.columnSpan: 1
                            Text { text: modelData[0]; color: Theme.faint; font.pixelSize: 12; Layout.preferredWidth: 96 }
                            Text { text: modelData[1]; color: Theme.fg; font.pixelSize: 13; elide: Text.ElideRight
                                   Layout.maximumWidth: 210 }
                        }
                    }
                }
            }
        }
    }

    // --- Диск точками ----------------------------------------------------------------------------
    Card {
        title: "Место на диске"
        subtitle: "Занято " + root.info.diskUsed + " из " + root.info.diskTotal + " · свободно " + root.info.diskFree
        Flow {
            Layout.fillWidth: true
            spacing: 5
            Repeater {
                model: 60
                Rectangle {
                    required property int index
                    width: 9; height: 9; radius: 4.5
                    color: index < Math.round(root.info.diskPercent * 0.6)
                           ? (root.info.diskPercent > 90 ? Theme.bad : Theme.fg) : Theme.line
                }
            }
        }
        RowLayout {
            spacing: 8
            Btn { text: "Очистить систему"; small: true; onClicked: backend.runButton("quick_action", "clean") }
            Btn { text: "Что занимает место"; small: true; onClicked: backend.runButton("quick_action", "space") }
        }
    }

    // --- Плитки состояния -------------------------------------------------------------------------
    GridLayout {
        Layout.fillWidth: true
        columns: width > 700 ? 3 : 2
        columnSpacing: 14
        rowSpacing: 14

        Repeater {
            model: [
                {page: "system", title: "Обновления",
                 value: root.upd.available ? "Есть новая версия" : root.upd.staged ? "Ждёт перезагрузки" : "Всё свежее",
                 kind: root.upd.available || root.upd.staged ? "accent" : "ok"},
                {page: "network", title: "VPN",
                 value: root.vpn.vpn ? "Включён" : root.vpn.proxy ? "Через прокси" : "Выключен",
                 kind: root.vpn.vpn ? "ok" : ""},
                {page: "laptop", title: root.laptop.batteries.length ? "Батарея" : "Питание",
                 value: root.laptop.batteries.length ? root.laptop.batteries[0].percent + "% · " + root.laptop.batteries[0].status.toLowerCase()
                                                     : ({"power-saver": "Тихо", "balanced": "Баланс", "performance": "Мощно"}[root.laptop.profile] || "Баланс"),
                 kind: "ok"},
                {page: "windows", title: "Переезд с Windows", value: "Файлы, закладки, обои", kind: ""},
                {page: "games", title: "Игры", value: "Steam, Proton, NVIDIA", kind: ""},
                {page: "assistant", title: "Помощник", value: "Спросите что угодно", kind: "accent"}
            ]
            Rectangle {
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: 92
                radius: 20
                color: tileMouse.containsMouse ? Theme.surfaceHover : Theme.surface
                border.width: 1
                border.color: Theme.line
                Behavior on color { ColorAnimation { duration: 120 } }
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 6
                    RowLayout {
                        Text { text: modelData.title; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                        StatusDot { kind: modelData.kind }
                    }
                    Text { text: modelData.value; color: Theme.fg; font.pixelSize: 16; font.weight: Font.DemiBold
                           elide: Text.ElideRight; Layout.fillWidth: true }
                }
                MouseArea { id: tileMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: app.page = modelData.page }
            }
        }
    }
}
