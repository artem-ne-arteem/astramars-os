import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "POWER"
    caption: "Батарея, яркость и профили питания. На обычном компьютере здесь только профили."

    property var l: backend.laptopInfo()
    property int limitDraft: l.batteries.length ? l.batteries[0].limit : 100
    Connections {
        target: backend
        function onChanged(what) { if (what === "laptop") root.l = backend.laptopInfo() }
    }
    Timer { interval: 10000; repeat: true; running: true; onTriggered: root.l = backend.laptopInfo() }

    Repeater {
        model: root.l.batteries
        Card {
            id: bat
            required property var modelData
            title: "Батарея · " + modelData.percent + "%"
            subtitle: modelData.status + (modelData.time ? " · " + modelData.time : "")
            badge: modelData.health ? "здоровье " + modelData.health + "%" : ""
            // заряд точками: 25 точек
            Row {
                spacing: 6
                Repeater {
                    model: 25
                    Rectangle {
                        required property int index
                        width: 14; height: 26; radius: 5
                        color: index < Math.round(bat.modelData.percent / 4)
                               ? (bat.modelData.percent <= 15 ? Theme.bad : bat.modelData.status === "Заряжается" ? Theme.ok : Theme.fg)
                               : index === Math.round(bat.modelData.limit / 4) - 1 && bat.modelData.limit < 100 ? Theme.soft(Theme.accent, 0.5)
                               : Theme.line
                    }
                }
            }
        }
    }

    Card {
        visible: root.l.batteries.length > 0
        title: "Беречь батарею"
        subtitle: root.l.batteries.length && root.l.batteries[0].limitSupported
                  ? "Если ноутбук почти всегда на зарядке, ограничьте заряд до 80% — батарея прослужит заметно дольше"
                  : "Этот ноутбук не позволяет ограничить заряд"
        enabled: root.l.batteries.length && root.l.batteries[0].limitSupported
        opacity: enabled ? 1 : 0.5
        Seg {
            model: [{id: "60", name: "60%"}, {id: "80", name: "80%"}, {id: "90", name: "90%"}, {id: "100", name: "Без ограничения"}]
            current: String(root.limitDraft)
            onPicked: function (id) { root.limitDraft = parseInt(id); backend.setChargeLimit(parseInt(id)) }
        }
    }

    Card {
        title: "Профиль питания"
        visible: root.l.profiles.length > 0
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: root.l.profiles
                Rectangle {
                    id: pr
                    required property var modelData
                    readonly property bool on: root.l.profile === modelData.id
                    Layout.fillWidth: true
                    implicitHeight: 84
                    radius: 18
                    color: on ? Theme.soft(Theme.accent, 0.12) : prMouse.containsMouse ? Theme.surfaceHover : Theme.surface2
                    border.width: 1
                    border.color: on ? Theme.soft(Theme.accent, 0.6) : Theme.line
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 4
                        Row {
                            spacing: 4
                            Repeater {
                                model: 3
                                Rectangle {
                                    required property int index
                                    width: 6; height: 6; radius: 3
                                    color: index <= ["power-saver", "balanced", "performance"].indexOf(pr.modelData.id)
                                           ? (pr.on ? Theme.accent : Theme.fg) : Theme.line
                                }
                            }
                        }
                        Text { text: pr.modelData.name; color: Theme.fg; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Text { text: pr.modelData.hint; color: Theme.muted; font.pixelSize: 12 }
                    }
                    MouseArea { id: prMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: backend.setProfile(pr.modelData.id) }
                }
            }
        }
    }

    Card {
        visible: root.l.brightness >= 0
        title: "Яркость экрана · " + Math.round(slider.value) + "%"
        Slider {
            id: slider
            Layout.fillWidth: true
            from: 1; to: 100
            value: root.l.brightness
            onMoved: backend.setBrightness(Math.round(value))
            background: Rectangle {
                x: slider.leftPadding; y: slider.topPadding + slider.availableHeight / 2 - 3
                width: slider.availableWidth; height: 6; radius: 3; color: Theme.line
                Rectangle { width: slider.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.accent }
            }
            handle: Rectangle {
                x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: 22; height: 22; radius: 11; color: "#ffffff"
            }
        }
    }

    Btn { text: "Энергосбережение и сон…"; onClicked: backend.openKde("kcm_powerdevilprofilesconfig") }
}
