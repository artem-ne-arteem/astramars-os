import QtQuick
import QtQuick.Layouts

// Точечные часы в духе Nothing: дата с красной точкой, крупное время шрифтом Doto,
// под ним полоска из 24 точек — сколько прошло суток.
Item {
    id: root
    property date now: new Date()
    readonly property real unit: Math.min(width / 7, height / 2.6)

    Timer {
        interval: 1000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: root.now = new Date()
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: root.unit * 0.12

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: root.unit * 0.12
            Rectangle {
                width: root.unit * 0.12; height: width; radius: width / 2
                color: "#ff3b30"
            }
            Text {
                text: root.now.toLocaleDateString(Qt.locale(), "dddd, d MMMM").toUpperCase()
                color: "#d9d9d9"
                font.family: "Inter"
                font.pixelSize: root.unit * 0.22
                font.letterSpacing: root.unit * 0.02
                font.weight: Font.DemiBold
            }
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatTime(root.now, "hh:mm")
            color: "#ffffff"
            font.family: "Doto"
            font.pixelSize: root.unit * 1.5
            font.weight: Font.Black
            style: Text.Raised
            styleColor: Qt.rgba(0, 0, 0, 0.35)
        }

        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: root.unit * 0.07
            Repeater {
                model: 24
                Rectangle {
                    width: root.unit * 0.09; height: width; radius: width / 2
                    color: index < root.now.getHours() ? "#ffffff"
                         : index === root.now.getHours() ? "#ff3b30" : Qt.rgba(1, 1, 1, 0.18)
                }
            }
        }
    }
}
