import QtQuick
import QtQuick.Layouts
import "."

RowLayout {
    id: r
    property string title: ""
    property string hint: ""
    property bool checked: false
    signal toggled(bool value)

    spacing: 14
    ColumnLayout {
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        spacing: 2
        Text {
            Layout.fillWidth: true
            text: r.title
            font.pixelSize: 14
            color: Theme.fg
            wrapMode: Text.WordWrap
        }
        Text {
            Layout.fillWidth: true
            text: r.hint
            visible: text !== ""
            font.pixelSize: 12
            color: Theme.muted
            wrapMode: Text.WordWrap
        }
    }
    Toggle {
        checked: r.checked
        onToggled: (value) => r.toggled(value)
    }
}
