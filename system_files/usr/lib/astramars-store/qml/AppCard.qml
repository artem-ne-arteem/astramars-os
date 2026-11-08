import QtQuick
import QtQuick.Layouts
import "."

// Карточка приложения: иконка, название, описание и одна кнопка
Rectangle {
    id: card
    property string appId: ""
    property string name: ""
    property string summary: ""
    property string icon: ""
    property string developer: ""
    property string state_: "available"    // available | installed | queued | installing | removing
    property int progress: 0
    signal installClicked()
    signal openClicked()
    signal removeClicked()

    readonly property bool busy: state_ === "queued" || state_ === "installing" || state_ === "removing"

    radius: 22
    color: mouse.containsMouse ? Theme.surfaceHover : Theme.surface
    border.width: 1
    border.color: busy ? Qt.rgba(1, 0.23, 0.19, 0.45) : Theme.line
    Behavior on color { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 200 } }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            // Иконка или буква на сером квадрате
            Item {
                Layout.preferredWidth: 60
                Layout.preferredHeight: 60
                Layout.alignment: Qt.AlignTop
                Image {
                    id: img
                    anchors.fill: parent
                    source: card.icon
                    sourceSize: Qt.size(128, 128)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    asynchronous: true
                    visible: status === Image.Ready
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 16
                    visible: img.status !== Image.Ready
                    color: Theme.surface2
                    Text {
                        anchors.centerIn: parent
                        text: card.name.charAt(0).toUpperCase()
                        font.family: Theme.dots
                        font.pixelSize: 30
                        font.weight: Font.Bold
                        color: Theme.fg
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 3
                Text {
                    Layout.fillWidth: true
                    text: card.name
                    elide: Text.ElideRight
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                    color: Theme.fg
                }
                Text {
                    Layout.fillWidth: true
                    text: card.summary
                    visible: text !== ""
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    font.pixelSize: 13
                    lineHeight: 1.15
                    color: Theme.muted
                }
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                Layout.fillWidth: true
                text: card.developer
                elide: Text.ElideRight
                font.pixelSize: 12
                color: Theme.faint
                visible: !card.busy
            }

            // Прогресс установки/удаления
            ColumnLayout {
                Layout.fillWidth: true
                visible: card.busy
                spacing: 6
                Text {
                    text: card.state_ === "queued" ? "В очереди…"
                        : card.state_ === "removing" ? "Удаляю…"
                        : (card.progress > 0 ? "Устанавливаю · " + card.progress + "%" : "Устанавливаю…")
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    color: Theme.fg
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 4
                    radius: 2
                    color: Theme.surface2
                    Rectangle {
                        height: parent.height
                        radius: 2
                        color: Theme.accent
                        width: card.state_ === "installing" && card.progress > 0
                               ? parent.width * card.progress / 100 : parent.width * 0.3
                        Behavior on width { NumberAnimation { duration: 250 } }
                        // Бегущий отрезок, пока процент неизвестен
                        SequentialAnimation on x {
                            running: card.busy && !(card.state_ === "installing" && card.progress > 0)
                            loops: Animation.Infinite
                            NumberAnimation { from: 0; to: parent ? parent.width * 0.7 : 0; duration: 900; easing.type: Easing.InOutSine }
                            NumberAnimation { to: 0; duration: 900; easing.type: Easing.InOutSine }
                        }
                        onVisibleChanged: x = 0
                    }
                }
            }

            // Удалить (только у установленных, при наведении)
            Rectangle {
                visible: card.state_ === "installed"
                opacity: mouse.containsMouse || trashMouse.containsMouse ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 150 } }
                implicitWidth: 38
                implicitHeight: 38
                radius: 19
                color: trashMouse.containsMouse ? Qt.rgba(1, 0.23, 0.19, 0.18) : Theme.glass
                Image {
                    anchors.centerIn: parent
                    source: "assets/trash.svg"
                    sourceSize: Qt.size(36, 36)
                    width: 18; height: 18
                }
                MouseArea {
                    id: trashMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: card.removeClicked()
                }
            }

            // Главная кнопка
            Rectangle {
                visible: !card.busy
                implicitWidth: btnText.implicitWidth + 36
                implicitHeight: 38
                radius: 19
                readonly property bool primary: card.state_ === "available"
                color: primary ? (btnMouse.containsMouse ? "#ffffff" : Theme.fg)
                               : (btnMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Theme.glass)
                border.width: primary ? 0 : 1
                border.color: Theme.line
                scale: btnMouse.pressed ? 0.96 : 1
                Behavior on scale { NumberAnimation { duration: 100 } }
                Text {
                    id: btnText
                    anchors.centerIn: parent
                    text: card.state_ === "installed" ? "Открыть" : "Установить"
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    color: parent.primary ? Theme.bg : Theme.fg
                }
                MouseArea {
                    id: btnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: card.state_ === "installed" ? card.openClicked() : card.installClicked()
                }
            }
        }
    }
}
