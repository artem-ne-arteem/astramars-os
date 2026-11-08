import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Страница настроек: крупный заголовок точками и прокручиваемое содержимое
Flickable {
    id: page
    property string heading: ""
    property string caption: ""
    default property alias content: column.data
    contentHeight: column.implicitHeight + 64
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    ColumnLayout {
        id: column
        x: 36
        y: 28
        width: Math.max(320, Math.min(page.width - 72, 880))
        spacing: 16
        Text {
            text: page.heading; color: Theme.fg; font.family: Theme.dots; font.pixelSize: 40
            font.weight: Font.Black; Layout.bottomMargin: -6
        }
        Text {
            visible: page.caption !== ""; text: page.caption; color: Theme.muted; font.pixelSize: 14
            wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.bottomMargin: 6
        }
    }
}
