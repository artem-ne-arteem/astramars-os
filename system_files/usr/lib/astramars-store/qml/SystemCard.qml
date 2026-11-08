import QtQuick
import QtQuick.Layouts
import "."

// Карточка обновления системы: версия, дата сборки, состояние и одна кнопка
Rectangle {
    id: card
    property var info: ({})
    signal checkClicked()
    signal updateClicked()
    signal rebootClicked()

    readonly property string st: info.state || "unknown"
    readonly property bool busy: st === "checking" || st === "downloading"

    implicitHeight: 128
    radius: 24
    color: Theme.surface
    border.width: 1
    border.color: st === "ready" ? Qt.rgba(1, 0.23, 0.19, 0.55) : Theme.line

    RowLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 20

        // Значок: «OS» из точек на чёрном квадрате
        Rectangle {
            Layout.preferredWidth: 84
            Layout.preferredHeight: 84
            radius: 22
            color: "#050505"
            border.color: Theme.line
            Text {
                anchors.centerIn: parent
                text: "OS"
                font.family: Theme.dots
                font.pixelSize: 34
                font.weight: Font.Bold
                font.variableAxes: ({ "ROND": 100, "wght": 700 })
                color: Theme.fg
            }
            Rectangle {
                width: 10; height: 10; radius: 5
                anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 10
                color: Theme.accent
                visible: card.st === "available" || card.st === "ready"
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            spacing: 4
            Text {
                text: card.info.name || "AstraMars OS"
                font.pixelSize: 20
                font.weight: Font.Bold
                color: Theme.fg
            }
            Text {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: card.st === "checking" ? "Проверяю, есть ли новая версия…"
                    : card.st === "downloading" ? "Скачиваю обновление — можно продолжать работать"
                    : card.st === "available" ? "Доступна новая версия системы"
                    : card.st === "ready" ? "Новая версия скачана" + (card.info.newBuilt ? " (сборка от " + card.info.newBuilt + ")" : "")
                                            + " — применится после перезагрузки"
                    : card.st === "error" ? "Не получилось: " + (card.info.error || "").split("\n").slice(-1)[0]
                    : card.st === "current" ? "Установлена последняя версия" + (card.info.checked ? " · проверено в " + card.info.checked : "")
                    : "Нажмите «Проверить», чтобы узнать о новой версии"
                font.pixelSize: 14
                color: card.st === "error" ? Theme.accent : card.st === "ready" || card.st === "available" ? Theme.fg : Theme.muted
            }
            Text {
                text: card.info.built ? "Текущая сборка от " + card.info.built : ""
                visible: text !== "" && card.st !== "downloading"
                font.pixelSize: 12
                color: Theme.faint
            }
            // Ход скачивания
            ColumnLayout {
                Layout.fillWidth: true
                visible: card.st === "downloading"
                spacing: 6
                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    implicitHeight: 4
                    radius: 2
                    color: Theme.surface2
                    clip: true
                    Rectangle {
                        width: parent.width * 0.3
                        height: parent.height
                        radius: 2
                        color: Theme.accent
                        SequentialAnimation on x {
                            running: card.st === "downloading"
                            loops: Animation.Infinite
                            NumberAnimation { from: 0; to: parent ? parent.width * 0.7 : 0; duration: 1100; easing.type: Easing.InOutSine }
                            NumberAnimation { to: 0; duration: 1100; easing.type: Easing.InOutSine }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: card.info.line || ""
                    elide: Text.ElideMiddle
                    font.pixelSize: 11
                    font.family: "JetBrains Mono"
                    color: Theme.faint
                }
            }
        }

        // Кнопка
        Rectangle {
            visible: !card.busy
            implicitWidth: btn.implicitWidth + 40
            implicitHeight: 44
            radius: 22
            readonly property bool primary: card.st === "available" || card.st === "ready"
            color: primary ? (mouse.containsMouse ? "#ffffff" : Theme.fg)
                           : (mouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Theme.glass)
            border.width: primary ? 0 : 1
            border.color: Theme.line
            scale: mouse.pressed ? 0.96 : 1
            Behavior on scale { NumberAnimation { duration: 100 } }
            Text {
                id: btn
                anchors.centerIn: parent
                text: card.st === "available" ? "Обновить" : card.st === "ready" ? "Перезагрузить" : "Проверить"
                font.pixelSize: 15
                font.weight: Font.DemiBold
                color: parent.primary ? Theme.bg : Theme.fg
            }
            MouseArea {
                id: mouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: card.st === "available" ? card.updateClicked()
                         : card.st === "ready" ? card.rebootClicked() : card.checkClicked()
            }
        }
    }
}
