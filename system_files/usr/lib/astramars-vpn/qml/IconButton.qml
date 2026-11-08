import QtQuick
import QtQuick.Controls.Basic
import "."

Rectangle {
    id: b
    property string icon: ""
    property string tip: ""
    property bool spinning: false
    readonly property bool hovered: mouse.containsMouse
    signal clicked()

    implicitWidth: 36
    implicitHeight: 36
    radius: 12
    color: mouse.pressed ? Theme.line : mouse.containsMouse ? Theme.surface2 : "transparent"
    Behavior on color { ColorAnimation { duration: 120 } }
    Behavior on opacity { NumberAnimation { duration: 120 } }

    Image {
        id: img
        anchors.centerIn: parent
        width: 18; height: 18
        sourceSize: Qt.size(36, 36)
        source: b.icon ? "assets/" + b.icon + ".svg" : ""
        RotationAnimation on rotation {
            running: b.spinning
            loops: Animation.Infinite
            from: 0; to: 360; duration: 900
            onStopped: img.rotation = 0
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: b.clicked()
    }

    ToolTip.visible: b.tip !== "" && mouse.containsMouse
    ToolTip.text: b.tip
    ToolTip.delay: 600
}
