import QtQuick
import QtQuick.Layouts
import "."

// Строка настройки: подпись слева, элементы управления справа
RowLayout {
    id: r
    property string title: ""
    property string subtitle: ""
    default property alias trailing: right.data
    Layout.fillWidth: true
    spacing: 16
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2
        Text { text: r.title; color: Theme.fg; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Text {
            visible: r.subtitle !== ""; text: r.subtitle; color: Theme.muted; font.pixelSize: 12
            Layout.fillWidth: true; wrapMode: Text.WordWrap
        }
    }
    RowLayout { id: right; spacing: 8 }
}
