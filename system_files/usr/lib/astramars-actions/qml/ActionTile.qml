import QtQuick
import QtQuick.Layouts
import "."

// Плитка действия: нажали — выполняется по шагам, в конце — итог
Rectangle {
    id: tile
    property var action: ({})
    signal runClicked()
    signal detailsClicked()
    signal editClicked()

    readonly property string st: action.status || "idle"
    readonly property bool running: st === "running"

    radius: 24
    color: running ? Theme.surface2 : (mouse.containsMouse ? Theme.surfaceHover : Theme.surface)
    border.width: 1
    border.color: running ? Qt.rgba(1, 0.23, 0.19, 0.6)
                : st === "failed" ? Qt.rgba(1, 0.23, 0.19, 0.35) : Theme.line
    scale: mouse.pressed && !running ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 120 } }
    Behavior on color { ColorAnimation { duration: 150 } }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: tile.running ? Qt.BusyCursor : Qt.PointingHandCursor
        onClicked: if (!tile.running) tile.runClicked()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            // Значок в круге; во время выполнения круг «дышит» красным
            Rectangle {
                Layout.preferredWidth: 46
                Layout.preferredHeight: 46
                radius: 23
                color: tile.running ? Qt.rgba(1, 0.23, 0.19, 0.18) : Theme.glass
                border.width: 1
                border.color: Theme.line
                Image {
                    anchors.centerIn: parent
                    source: "assets/" + (tile.action.icon || "terminal") + ".svg"
                    sourceSize: Qt.size(48, 48)
                    width: 24; height: 24
                }
                SequentialAnimation on opacity {
                    running: tile.running
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.55; duration: 600; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 1; duration: 600; easing.type: Easing.InOutSine }
                    onStopped: parent.opacity = 1
                }
            }
            Item { Layout.fillWidth: true }
            Image {
                visible: tile.action.root === true
                source: "assets/lock.svg"
                sourceSize: Qt.size(32, 32)
                Layout.preferredWidth: 16; Layout.preferredHeight: 16
                opacity: 0.6
            }
            // Правка своего действия
            Rectangle {
                visible: tile.action.custom === true && !tile.running
                Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15
                color: editMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Image { anchors.centerIn: parent; source: "assets/edit.svg"; sourceSize: Qt.size(32, 32); width: 16; height: 16 }
                MouseArea { id: editMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: tile.editClicked() }
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.topMargin: 4
            text: tile.action.title || ""
            elide: Text.ElideRight
            font.pixelSize: 16
            font.weight: Font.DemiBold
            color: Theme.fg
        }

        // Описание → ход выполнения → итог
        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            verticalAlignment: Text.AlignTop
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
            text: tile.running ? (tile.action.stepTitle || "Выполняю") + "…"
                : (tile.st === "done" || tile.st === "failed") ? tile.action.summary
                : tile.action.subtitle || ""
            font.pixelSize: 13
            lineHeight: 1.15
            color: tile.st === "failed" ? Theme.accent : tile.st === "done" ? Theme.fg : Theme.muted
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Шаги точками: пройденные — белые, текущий — красный
            Row {
                visible: tile.running
                spacing: 5
                Repeater {
                    model: tile.action.steps || 0
                    delegate: Rectangle {
                        required property int index
                        width: 7; height: 7; radius: 3.5
                        color: index < tile.action.step ? Theme.fg : index === tile.action.step ? Theme.accent : Theme.line
                    }
                }
            }
            Text {
                visible: tile.running
                text: "шаг " + ((tile.action.step || 0) + 1) + " из " + (tile.action.steps || 0)
                font.pixelSize: 11
                color: Theme.faint
            }
            Text {
                visible: tile.st === "done" || tile.st === "failed"
                text: tile.st === "done" ? "✓ готово" : "✗ ошибка"
                font.pixelSize: 12
                font.weight: Font.DemiBold
                color: tile.st === "done" ? "#3fd28b" : Theme.accent
            }
            Item { Layout.fillWidth: true }
            Text {
                visible: tile.action.hasLog === true && !tile.running
                text: "Подробнее"
                font.pixelSize: 12
                font.underline: detMouse.containsMouse
                color: Theme.muted
                MouseArea { id: detMouse; anchors.fill: parent; anchors.margins: -6; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: tile.detailsClicked() }
            }
        }
    }
}
