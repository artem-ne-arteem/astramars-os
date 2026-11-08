import QtQuick
import "."

// Переключатель режима: VPN (весь компьютер) или прокси (порт 2080)
Rectangle {
    id: sw
    property string mode: "tun"
    signal picked(string mode)

    implicitHeight: 46
    radius: height / 2
    color: Theme.surface
    border.color: Theme.line

    readonly property var options: [
        { key: "tun", title: "VPN", hint: "весь компьютер" },
        { key: "proxy", title: "Прокси", hint: "порт 2080" }
    ]

    Rectangle {
        y: 4
        height: parent.height - 8
        width: (parent.width - 8) / 2
        x: sw.mode === "tun" ? 4 : parent.width / 2
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.mars }
            GradientStop { position: 1; color: Theme.marsLight }
        }
        Behavior on x { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }
    }

    Row {
        anchors.fill: parent
        anchors.margins: 4
        Repeater {
            model: sw.options
            delegate: Item {
                required property var modelData
                readonly property bool active: sw.mode === modelData.key
                width: (sw.width - 8) / 2
                height: sw.height - 8
                Row {
                    anchors.centerIn: parent
                    spacing: 6
                    Text {
                        id: titleText
                        text: modelData.title
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        color: active ? Theme.inkOnMars : Theme.fg
                        Behavior on color { ColorAnimation { duration: 200 } }
                    }
                    Text {
                        anchors.baseline: titleText.baseline
                        text: modelData.hint
                        font.pixelSize: 12
                        color: active ? Qt.rgba(0.11, 0.05, 0.02, 0.7) : Theme.muted
                        Behavior on color { ColorAnimation { duration: 200 } }
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: sw.picked(modelData.key)
                }
            }
        }
    }
}
