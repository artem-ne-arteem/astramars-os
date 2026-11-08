import QtQuick
import QtQuick.Shapes
import "."

// Кнопка подключения — уголёк Ygolek. Выключено: остывший уголь.
// Подключение: трещины и глаза пульсируют. Подключено: уголёк горит синим.
Item {
    id: coal
    property string status: "off"
    signal clicked()

    readonly property bool on: status === "on"
    readonly property bool busy: status === "connecting"
    readonly property bool failed: status === "error"

    implicitWidth: 240
    implicitHeight: 240

    // Насколько разгорелся уголёк: 0 — холодный, 1 — горит
    property real heat: on ? 1 : 0
    Behavior on heat { NumberAnimation { duration: 700; easing.type: Easing.InOutQuad } }
    property real pulse: 0
    SequentialAnimation on pulse {
        running: coal.busy
        loops: Animation.Infinite
        NumberAnimation { from: 0.15; to: 1; duration: 600; easing.type: Easing.InOutSine }
        NumberAnimation { from: 1; to: 0.15; duration: 600; easing.type: Easing.InOutSine }
        onStopped: coal.pulse = 0
    }
    readonly property real light: Math.max(heat, busy ? pulse : 0)
    readonly property color fire: failed ? Theme.danger : Theme.glow
    readonly property color crackColor: failed ? Qt.rgba(0.94, 0.32, 0.32, 0.8)
                                               : Qt.tint("#2a3550", Qt.rgba(0.49, 0.77, 1, light))

    // Свечение
    Rectangle {
        anchors.centerIn: parent
        width: 230; height: 230; radius: width / 2
        color: coal.fire
        opacity: 0.05 + coal.light * 0.13
        SequentialAnimation on scale {
            running: coal.on
            loops: Animation.Infinite
            NumberAnimation { to: 1.06; duration: 2000; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.98; duration: 2000; easing.type: Easing.InOutSine }
        }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 176; height: 176; radius: width / 2
        color: coal.fire
        opacity: coal.light * 0.12
    }

    // Искра на орбите
    Rectangle {
        anchors.centerIn: parent
        width: 216; height: 216; radius: width / 2
        color: "transparent"
        border.width: 1.5
        border.color: coal.on ? Qt.rgba(0.49, 0.77, 1, 0.35) : coal.failed ? Qt.rgba(0.94, 0.32, 0.32, 0.35) : Theme.line
        Behavior on border.color { ColorAnimation { duration: 500 } }
    }
    Item {
        id: orbit
        anchors.centerIn: parent
        width: 216; height: 216
        Rectangle {
            width: 8; height: 8; radius: 4
            x: (parent.width - width) / 2
            y: -height / 2
            color: Theme.glow
            opacity: coal.on || coal.busy ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 400 } }
            Rectangle { anchors.centerIn: parent; width: 20; height: 20; radius: 10; color: Theme.glow; opacity: 0.25 }
        }
    }
    RotationAnimation {
        target: orbit; property: "rotation"
        running: coal.busy; loops: Animation.Infinite
        from: orbit.rotation; to: orbit.rotation + 360; duration: 1200
    }
    RotationAnimation {
        target: orbit; property: "rotation"
        running: coal.on; loops: Animation.Infinite
        from: orbit.rotation; to: orbit.rotation + 360; duration: 14000
    }

    // Сам уголёк (координаты логотипа 640×640, масштабируется)
    Item {
        id: body
        anchors.centerIn: parent
        width: 176; height: 176
        scale: mouse.pressed ? 0.94 : mouse.containsMouse ? 1.04 : 1
        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

        Shape {
            width: 640; height: 640
            x: -width * (1 - body.width / 640) / 2
            y: -height * (1 - body.height / 640) / 2
            scale: body.width / 640
            layer.enabled: true
            layer.samples: 8

            // Камень
            ShapePath {
                strokeColor: Qt.tint("#1f2738", Qt.rgba(0.49, 0.77, 1, coal.light * 0.5))
                strokeWidth: 6
                joinStyle: ShapePath.MiterJoin
                fillGradient: LinearGradient {
                    x1: 160; y1: 120; x2: 480; y2: 520
                    GradientStop { position: 0; color: "#1b2233" }
                    GradientStop { position: 1; color: "#06080e" }
                }
                startX: 268; startY: 128
                PathLine { x: 332; y: 116 }
                PathLine { x: 410; y: 158 }
                PathLine { x: 432; y: 214 }
                PathLine { x: 482; y: 248 }
                PathLine { x: 500; y: 328 }
                PathLine { x: 524; y: 352 }
                PathLine { x: 494; y: 424 }
                PathLine { x: 442; y: 470 }
                PathLine { x: 332; y: 518 }
                PathLine { x: 232; y: 502 }
                PathLine { x: 178; y: 470 }
                PathLine { x: 132; y: 410 }
                PathLine { x: 104; y: 356 }
                PathLine { x: 126; y: 300 }
                PathLine { x: 140; y: 240 }
                PathLine { x: 172; y: 194 }
                PathLine { x: 216; y: 180 }
                PathLine { x: 268; y: 128 }
            }

            // Трещины: широкая полупрозрачная «подсветка» и яркая сердцевина
            ShapePath {
                strokeColor: Qt.rgba(0.49, 0.77, 1, coal.light * 0.28)
                strokeWidth: 26; fillColor: "transparent"
                capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                startX: 302; startY: 168
                PathLine { x: 252; y: 214 }
                PathLine { x: 258; y: 248 }
                PathLine { x: 206; y: 282 }
                PathMove { x: 158; y: 392 }
                PathLine { x: 204; y: 440 }
                PathLine { x: 244; y: 456 }
                PathMove { x: 482; y: 350 }
                PathLine { x: 470; y: 402 }
                PathLine { x: 436; y: 432 }
            }
            ShapePath {
                strokeColor: coal.crackColor
                strokeWidth: 9; fillColor: "transparent"
                capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                startX: 302; startY: 168
                PathLine { x: 252; y: 214 }
                PathLine { x: 258; y: 248 }
                PathLine { x: 206; y: 282 }
                PathMove { x: 158; y: 392 }
                PathLine { x: 204; y: 440 }
                PathLine { x: 244; y: 456 }
                PathMove { x: 482; y: 350 }
                PathLine { x: 470; y: 402 }
                PathLine { x: 436; y: 432 }
            }

            // Глаза
            ShapePath {
                strokeColor: Qt.rgba(0.49, 0.77, 1, coal.light * 0.3)
                strokeWidth: 18; joinStyle: ShapePath.RoundJoin
                fillColor: coal.failed ? Theme.danger : Qt.tint("#3a465e", Qt.rgba(0.85, 0.93, 1, coal.light))
                startX: 218; startY: 312
                PathLine { x: 284; y: 338 }
                PathLine { x: 276; y: 378 }
                PathLine { x: 240; y: 384 }
                PathLine { x: 222; y: 356 }
                PathLine { x: 218; y: 312 }
                PathMove { x: 432; y: 312 }
                PathLine { x: 366; y: 338 }
                PathLine { x: 374; y: 378 }
                PathLine { x: 410; y: 384 }
                PathLine { x: 428; y: 356 }
                PathLine { x: 432; y: 312 }
            }
        }
    }

    MouseArea {
        id: mouse
        anchors.centerIn: parent
        width: 190; height: 190
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: coal.clicked()
    }
}
