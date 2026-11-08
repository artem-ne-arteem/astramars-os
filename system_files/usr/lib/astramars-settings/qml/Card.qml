import QtQuick
import QtQuick.Layouts
import "."

// Карточка раздела: заголовок, пояснение и содержимое столбиком
Rectangle {
    id: card
    property string title: ""
    property string subtitle: ""
    property string badge: ""
    default property alias content: body.data
    property alias spacing: body.spacing

    Layout.fillWidth: true
    implicitHeight: col.implicitHeight + 40
    radius: 22
    color: Theme.surface
    border.width: 1
    border.color: Theme.line

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 20
        spacing: 14
        RowLayout {
            visible: card.title !== ""
            Layout.fillWidth: true
            spacing: 10
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text {
                    text: card.title; color: Theme.fg; font.pixelSize: 16; font.weight: Font.DemiBold
                    Layout.fillWidth: true; elide: Text.ElideRight
                }
                Text {
                    visible: card.subtitle !== ""; text: card.subtitle; color: Theme.muted; font.pixelSize: 13
                    wrapMode: Text.WordWrap; Layout.fillWidth: true
                }
            }
            Rectangle {
                visible: card.badge !== ""
                radius: 11
                color: Theme.soft(Theme.accent, 0.16)
                implicitWidth: badgeText.implicitWidth + 18
                implicitHeight: 22
                Text {
                    id: badgeText; anchors.centerIn: parent; text: card.badge; color: Theme.accent
                    font.pixelSize: 11; font.weight: Font.DemiBold
                }
            }
        }
        ColumnLayout { id: body; Layout.fillWidth: true; spacing: 12 }
    }
}
