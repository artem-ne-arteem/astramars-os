import QtQuick
import "."

Item {
    id: t
    property bool checked: false
    signal toggled(bool value)

    implicitWidth: 46
    implicitHeight: 26

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: t.checked ? Theme.accent : Theme.line
        Behavior on color { ColorAnimation { duration: 180 } }
    }
    Rectangle {
        width: 20; height: 20; radius: 10
        y: 3
        x: t.checked ? t.width - width - 3 : 3
        color: "#ffffff"
        Behavior on x { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: t.toggled(!t.checked)
    }
}
