import QtQuick
import QtQuick.Shapes
import "."

// Кнопка подключения: планета Марс с ушками (Марсик), по орбите летит звезда (Астра)
Item {
    id: orb
    property string status: "off"
    signal clicked()

    readonly property bool on: status === "on"
    readonly property bool busy: status === "connecting"
    readonly property bool failed: status === "error"

    implicitWidth: 248
    implicitHeight: 248

    property color c1: on || busy ? "#ffb07a" : "#4c4462"
    property color c2: on || busy ? "#ff7a45" : "#2d2841"
    property color c3: on || busy ? "#8f2a0e" : "#15121f"
    Behavior on c1 { ColorAnimation { duration: 600 } }
    Behavior on c2 { ColorAnimation { duration: 600 } }
    Behavior on c3 { ColorAnimation { duration: 600 } }

    // Свечение
    Rectangle {
        anchors.centerIn: parent
        width: 236; height: 236; radius: width / 2
        color: orb.failed ? Theme.danger : Theme.mars
        opacity: orb.on ? 0.16 : orb.busy ? 0.1 : orb.failed ? 0.08 : 0
        Behavior on opacity { NumberAnimation { duration: 600 } }
        SequentialAnimation on scale {
            running: orb.on || orb.busy
            loops: Animation.Infinite
            NumberAnimation { to: 1.06; duration: 1800; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.97; duration: 1800; easing.type: Easing.InOutSine }
        }
    }

    // Орбита
    Rectangle {
        anchors.centerIn: parent
        width: 220; height: 220; radius: width / 2
        color: "transparent"
        border.width: 1.5
        border.color: orb.on ? Qt.rgba(1, 0.85, 0.48, 0.5) : orb.failed ? Qt.rgba(1, 0.42, 0.42, 0.4) : Theme.line
        Behavior on border.color { ColorAnimation { duration: 500 } }
    }

    // Звезда на орбите
    Item {
        id: orbit
        anchors.centerIn: parent
        width: 220; height: 220
        Text {
            text: "✦"
            color: Theme.astra
            font.pixelSize: 22
            x: (parent.width - width) / 2
            y: -height / 2
            opacity: orb.on || orb.busy ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 500 } }
        }
    }
    RotationAnimation {
        target: orbit; property: "rotation"
        running: orb.busy; loops: Animation.Infinite
        from: orbit.rotation; to: orbit.rotation + 360; duration: 1300
    }
    RotationAnimation {
        target: orbit; property: "rotation"
        running: orb.on; loops: Animation.Infinite
        from: orbit.rotation; to: orbit.rotation + 360; duration: 16000
    }

    // Планета с ушками
    Item {
        id: body
        anchors.fill: parent
        scale: mouse.pressed ? 0.95 : mouse.containsMouse ? 1.03 : 1
        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

        Shape {
            anchors.fill: parent
            layer.enabled: true
            layer.samples: 8
            ShapePath {
                fillColor: orb.c2; strokeColor: "transparent"
                startX: 68; startY: 104
                PathLine { x: 78; y: 42 }
                PathLine { x: 118; y: 74 }
                PathLine { x: 68; y: 104 }
            }
            ShapePath {
                fillColor: orb.c2; strokeColor: "transparent"
                startX: 180; startY: 104
                PathLine { x: 170; y: 42 }
                PathLine { x: 130; y: 74 }
                PathLine { x: 180; y: 104 }
            }
            ShapePath {
                fillColor: Qt.rgba(1, 0.8, 0.7, orb.on || orb.busy ? 0.35 : 0.08); strokeColor: "transparent"
                startX: 82; startY: 90
                PathLine { x: 86; y: 58 }
                PathLine { x: 106; y: 76 }
                PathLine { x: 82; y: 90 }
            }
            ShapePath {
                fillColor: Qt.rgba(1, 0.8, 0.7, orb.on || orb.busy ? 0.35 : 0.08); strokeColor: "transparent"
                startX: 166; startY: 90
                PathLine { x: 162; y: 58 }
                PathLine { x: 142; y: 76 }
                PathLine { x: 166; y: 90 }
            }
        }

        Rectangle {
            id: planet
            anchors.centerIn: parent
            anchors.verticalCenterOffset: 10
            width: 152; height: 152; radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: orb.c1 }
                GradientStop { position: 0.55; color: orb.c2 }
                GradientStop { position: 1.0; color: orb.c3 }
            }
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.06)

            // Кратеры и блик
            Rectangle { x: 30; y: 92; width: 26; height: 16; radius: 8; color: "#000000"; opacity: 0.13 }
            Rectangle { x: 100; y: 104; width: 20; height: 12; radius: 6; color: "#000000"; opacity: 0.12 }
            Rectangle { x: 108; y: 40; width: 12; height: 8; radius: 4; color: "#000000"; opacity: 0.1 }
            Rectangle { x: 26; y: 18; width: 54; height: 34; radius: 17; color: "#ffffff"; opacity: 0.07; rotation: -30 }

            // Значок питания
            Shape {
                anchors.centerIn: parent
                width: 60; height: 60
                layer.enabled: true
                layer.samples: 8
                opacity: orb.busy ? pulse.value : 1
                ShapePath {
                    strokeColor: orb.on || orb.busy ? "#fff4e8" : "#a59cbc"
                    strokeWidth: 5
                    capStyle: ShapePath.RoundCap
                    fillColor: "transparent"
                    PathAngleArc { centerX: 30; centerY: 32; radiusX: 20; radiusY: 20; startAngle: -55; sweepAngle: 290 }
                }
                ShapePath {
                    strokeColor: orb.on || orb.busy ? "#fff4e8" : "#a59cbc"
                    strokeWidth: 5
                    capStyle: ShapePath.RoundCap
                    fillColor: "transparent"
                    startX: 30; startY: 6
                    PathLine { x: 30; y: 28 }
                }
            }
        }
    }

    QtObject {
        id: pulse
        property real value: 1
        SequentialAnimation on value {
            running: orb.busy; loops: Animation.Infinite
            NumberAnimation { to: 0.35; duration: 500 }
            NumberAnimation { to: 1; duration: 500 }
        }
    }

    MouseArea {
        id: mouse
        anchors.centerIn: parent
        width: 180; height: 190
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: orb.clicked()
    }
}
