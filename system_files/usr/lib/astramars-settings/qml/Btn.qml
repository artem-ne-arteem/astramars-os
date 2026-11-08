import QtQuick
import "."

// Кнопка-«пилюля»: primary — акцентная, обычная — стеклянная, danger — красный текст
Rectangle {
    id: b
    property string text: ""
    property bool primary: false
    property bool danger: false
    property bool busy: false
    property bool small: false
    signal clicked()

    implicitWidth: Math.max(label.implicitWidth + (small ? 26 : 36), small ? 0 : 96)
    implicitHeight: small ? 30 : 38
    radius: height / 2
    opacity: enabled ? (busy ? pulse : 1) : 0.4
    property real pulse: 1
    color: primary ? (mouse.containsMouse ? Qt.lighter(Theme.accent, 1.12) : Theme.accent)
                   : (mouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Theme.glass)
    border.width: primary ? 0 : 1
    border.color: Theme.line
    scale: mouse.pressed ? 0.96 : 1
    Behavior on scale { NumberAnimation { duration: 100 } }
    Behavior on color { ColorAnimation { duration: 120 } }

    SequentialAnimation on pulse {
        running: b.busy
        loops: Animation.Infinite
        NumberAnimation { to: 0.5; duration: 500 }
        NumberAnimation { to: 1; duration: 500 }
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: b.busy ? "• • •" : b.text
        color: b.primary ? "#ffffff" : b.danger ? Theme.bad : Theme.fg
        font.pixelSize: b.small ? 12 : 14
        font.weight: Font.DemiBold
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (!b.busy) b.clicked()
    }
}
