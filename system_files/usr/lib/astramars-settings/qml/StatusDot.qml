import QtQuick
import "."

// Точка состояния: ok — зелёная, bad — красная, warn — оранжевая, accent; pulse — «идёт работа»
Rectangle {
    id: d
    property string kind: ""
    property bool pulse: false
    property real glow: 1
    width: 8
    height: 8
    radius: 4
    opacity: pulse ? glow : 1
    color: kind === "ok" ? Theme.ok : kind === "bad" ? Theme.bad : kind === "warn" ? Theme.warn
         : kind === "accent" ? Theme.accent : Theme.faint
    SequentialAnimation on glow {
        running: d.pulse
        loops: Animation.Infinite
        NumberAnimation { to: 0.25; duration: 550 }
        NumberAnimation { to: 1; duration: 550 }
    }
}
