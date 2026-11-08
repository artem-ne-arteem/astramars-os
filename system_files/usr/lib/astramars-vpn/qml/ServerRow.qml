import QtQuick
import QtQuick.Layouts
import "."

// Строка сервера: протокол, имя, адрес, пинг
Rectangle {
    id: row
    property var server: ({})
    property bool selected: false
    signal picked()
    signal removeRequested()

    implicitHeight: 64
    radius: 16
    color: selected ? Theme.surface2 : mouse.containsMouse ? Theme.surfaceHover : Theme.surface
    border.width: selected ? 1.5 : 1
    border.color: selected ? Theme.mars : Theme.line
    Behavior on color { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 150 } }

    readonly property int ping: server.ping === undefined ? -1 : server.ping
    readonly property string pingText: ping >= 0 ? ping + " мс" : ping === -2 ? "UDP" : ping === -3 ? "нет связи" : "—"
    readonly property color pingColor: ping >= 0 ? (ping < 150 ? Theme.ok : ping < 400 ? Theme.warn : Theme.mars)
                                                 : ping === -3 ? Theme.danger : Theme.faint

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: row.picked()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 8
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 58
            Layout.preferredHeight: 26
            radius: 8
            color: row.selected ? Qt.rgba(1, 0.48, 0.27, 0.16) : Theme.surface2
            Text {
                anchors.centerIn: parent
                text: row.server.protocol || ""
                font.family: Theme.mono
                font.pixelSize: 11
                font.weight: Font.Medium
                color: row.selected ? Theme.marsLight : Theme.astra
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            spacing: 2
            Text {
                Layout.fillWidth: true
                text: row.server.name || ""
                elide: Text.ElideRight
                font.pixelSize: 14
                font.weight: row.selected ? Font.DemiBold : Font.Normal
                color: Theme.fg
            }
            Text {
                Layout.fillWidth: true
                text: row.server.address || ""
                elide: Text.ElideMiddle
                font.family: Theme.mono
                font.pixelSize: 11
                color: Theme.muted
            }
        }

        Text {
            text: row.pingText
            font.family: Theme.mono
            font.pixelSize: 12
            color: row.pingColor
        }

        IconButton {
            icon: "trash"
            tip: "Удалить сервер"
            opacity: mouse.containsMouse || hovered ? 1 : 0
            visible: !(row.server.sub)
            onClicked: row.removeRequested()
        }
    }
}
