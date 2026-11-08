import QtQuick
import "."

// Раздел-«таблетка»: выбранный — белый с чёрным текстом, остальные — стеклянные
Rectangle {
    id: chip
    property string text: ""
    property bool active: false
    signal clicked()

    implicitHeight: 38
    implicitWidth: label.implicitWidth + 32
    radius: height / 2
    color: active ? Theme.fg : (mouse.containsMouse ? Qt.rgba(1, 1, 1, 0.1) : Theme.glass)
    border.width: active ? 0 : 1
    border.color: Theme.line
    Behavior on color { ColorAnimation { duration: 150 } }

    Text {
        id: label
        anchors.centerIn: parent
        text: chip.text
        font.pixelSize: 14
        font.weight: Font.DemiBold
        color: chip.active ? Theme.bg : Theme.fg
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: chip.clicked()
    }
}
