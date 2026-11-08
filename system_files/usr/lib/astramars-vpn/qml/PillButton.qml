import QtQuick
import "."

Rectangle {
    id: p
    property string text: ""
    property bool primary: true
    signal clicked()

    implicitHeight: 42
    implicitWidth: label.implicitWidth + 40
    radius: height / 2
    color: primary ? (mouse.containsMouse ? Theme.marsLight : Theme.mars)
                   : (mouse.containsMouse ? Theme.line : Theme.surface2)
    scale: mouse.pressed ? 0.97 : 1
    Behavior on color { ColorAnimation { duration: 120 } }
    Behavior on scale { NumberAnimation { duration: 100 } }

    Text {
        id: label
        anchors.centerIn: parent
        text: p.text
        font.pixelSize: 14
        font.weight: Font.DemiBold
        color: p.primary ? Theme.inkOnMars : Theme.fg
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: p.clicked()
    }
}
