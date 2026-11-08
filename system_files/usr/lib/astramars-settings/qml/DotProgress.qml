import QtQuick
import QtQuick.Layouts
import "."

// Ход долгой задачи: полоска из 20 точек и подпись. value < 0 — бегущий огонёк
ColumnLayout {
    id: p
    property int value: -1
    property string text: ""
    property int tick: 0
    spacing: 8
    Layout.fillWidth: true

    Timer {
        interval: 90; repeat: true
        running: p.visible && p.value < 0
        onTriggered: p.tick = (p.tick + 1) % 24
    }
    Row {
        spacing: 6
        Repeater {
            model: 20
            Rectangle {
                required property int index
                width: 8; height: 8; radius: 4
                color: p.value >= 0 ? (index < Math.round(p.value / 5) ? Theme.accent : Theme.line)
                                    : (Math.abs(index - p.tick + 2) < 2 ? Theme.accent : Theme.line)
                Behavior on color { ColorAnimation { duration: 120 } }
            }
        }
    }
    Text {
        visible: p.text !== ""; text: p.text; color: Theme.muted; font.pixelSize: 12
        Layout.fillWidth: true; elide: Text.ElideRight
    }
}
