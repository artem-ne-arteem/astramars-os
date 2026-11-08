import QtQuick
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "LOOK"
    caption: "Цвет акцента меняется во всей системе и в наших приложениях."

    property var accents: backend.accents()
    property var look: backend.appearance()
    Connections {
        target: backend
        function onChanged(what) { if (what === "accent" || what === "appearance") root.look = backend.appearance() }
    }

    Card {
        title: "Цвет акцента"
        subtitle: "Кнопки, переключатели, выделение и точка в часах"
        Flow {
            Layout.fillWidth: true
            spacing: 14
            Repeater {
                model: root.accents
                ColumnLayout {
                    id: sw
                    required property var modelData
                    readonly property bool on: root.look.accent === modelData.color
                    spacing: 8
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        width: 54; height: 54; radius: 27
                        color: "transparent"
                        border.width: 2
                        border.color: sw.on ? sw.modelData.color : "transparent"
                        Rectangle {
                            anchors.centerIn: parent
                            width: 40; height: 40; radius: 20
                            color: sw.modelData.color
                            scale: swMouse.containsMouse ? 1.08 : 1
                            Behavior on scale { NumberAnimation { duration: 120 } }
                            Rectangle { anchors.centerIn: parent; visible: sw.on; width: 10; height: 10; radius: 5; color: "#ffffff" }
                        }
                        MouseArea { id: swMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    onClicked: backend.setAccent(sw.modelData.color) }
                    }
                    Text { Layout.alignment: Qt.AlignHCenter; text: sw.modelData.name; font.pixelSize: 12
                           color: sw.on ? Theme.fg : Theme.muted }
                }
            }
        }
    }

    Card {
        title: "Тема"
        SettingRow {
            title: "Оформление окон и программ"
            subtitle: "Тёмная — фирменная для AstraMars"
            Seg {
                model: [{id: "dark", name: "Тёмная"}, {id: "light", name: "Светлая"}]
                current: root.look.scheme
                onPicked: function (id) { backend.setScheme(id) }
            }
        }
    }

    Card {
        title: "Обои по времени суток"
        subtitle: "Утром — рассвет, днём — светлее, вечером — закат, ночью — тёмные дюны"
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: [["morning", "Утро", "6–11"], ["day", "День", "11–17"], ["evening", "Вечер", "17–21"], ["night", "Ночь", "21–6"]]
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 6
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: width * 9 / 16
                        radius: 12
                        clip: true
                        color: Theme.surface2
                        Image {
                            anchors.fill: parent
                            source: wallpaperDir + "/" + modelData[0] + ".jpg"
                            sourceSize.width: 320
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                        }
                    }
                    Text { text: modelData[1] + "  ·  " + modelData[2]; color: Theme.muted; font.pixelSize: 12 }
                }
            }
        }
        SettingRow {
            title: "Менять обои сами"
            Toggle { checked: root.look.daytime; onToggled: function (v) { backend.setDaytime(v) } }
        }
    }

    Card {
        title: "Виджеты в стиле Nothing"
        subtitle: "Крупные точечные часы с датой и «полоской дня» на рабочем столе"
        RowLayout {
            spacing: 18
            Rectangle {
                Layout.preferredWidth: 260
                Layout.preferredHeight: 120
                radius: 16
                color: "#050505"
                border.width: 1
                border.color: Theme.line
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 6
                        Rectangle { width: 6; height: 6; radius: 3; color: Theme.accent }
                        Text { text: new Date().toLocaleDateString(Qt.locale("ru_RU"), "dddd, d MMMM").toUpperCase()
                               color: "#cfcfcf"; font.pixelSize: 10; font.weight: Font.DemiBold }
                    }
                    Text { Layout.alignment: Qt.AlignHCenter; text: Qt.formatTime(new Date(), "hh:mm")
                           color: "#ffffff"; font.family: Theme.dots; font.pixelSize: 48; font.weight: Font.Black }
                    Row {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 3
                        Repeater {
                            model: 24
                            Rectangle {
                                required property int index
                                width: 5; height: 5; radius: 2.5
                                color: index < new Date().getHours() ? "#ffffff" : index === new Date().getHours() ? Theme.accent : Qt.rgba(1, 1, 1, 0.18)
                            }
                        }
                    }
                }
            }
            ColumnLayout {
                spacing: 10
                Btn { text: "Добавить на рабочий стол"; primary: true; busy: app.running("clock"); onClicked: backend.addClock() }
                Btn { text: "Обои и рабочий стол…"; onClicked: backend.openWallpapers() }
            }
        }
    }
}
