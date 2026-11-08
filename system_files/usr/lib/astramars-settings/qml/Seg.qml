import QtQuick
import QtQuick.Layouts
import "."

// Переключатель вариантов: model — [{id, name}], current — id выбранного
Rectangle {
    id: seg
    property var model: []
    property string current: ""
    signal picked(string id)
    implicitHeight: 38
    implicitWidth: row.implicitWidth + 8
    radius: 19
    color: Theme.glass
    border.width: 1
    border.color: Theme.line

    RowLayout {
        id: row
        anchors.fill: parent
        anchors.margins: 4
        spacing: 2
        Repeater {
            model: seg.model
            Rectangle {
                id: opt
                required property var modelData
                readonly property bool on: modelData.id === seg.current
                Layout.fillWidth: true
                Layout.fillHeight: true
                implicitWidth: label.implicitWidth + 28
                radius: height / 2
                color: on ? Theme.fg : (m.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent")
                Behavior on color { ColorAnimation { duration: 150 } }
                Text {
                    id: label; anchors.centerIn: parent; text: opt.modelData.name; font.pixelSize: 13
                    font.weight: Font.DemiBold; color: opt.on ? "#000000" : Theme.fg
                }
                MouseArea {
                    id: m; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: seg.picked(opt.modelData.id)
                }
            }
        }
    }
}
