import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Окно при открытии .exe/.msi: заработает ли программа, установка Bottles, запуск
ApplicationWindow {
    id: app
    width: 560
    height: content.implicitHeight + 56
    minimumWidth: 480
    visible: false
    title: "Программа для Windows"
    color: Theme.bg
    flags: Qt.Dialog

    property var jobs: ({})
    function job(id) { return jobs[id] || ({state: "", pct: -1, text: ""}) }
    function running(id) { return job(id).state === "running" }
    property var v: backend.exeInfo(exePath)
    readonly property var j: job("exe")

    Connections {
        target: backend
        function onJob(id, state, pct, text) {
            var x = Object.assign({}, app.jobs); x[id] = {state: state, pct: pct, text: text}; app.jobs = x
            if (id === "exe" && state === "done") closeTimer.start()
        }
    }
    Timer { id: closeTimer; interval: 2500; onTriggered: Qt.quit() }

    ColumnLayout {
        id: content
        x: 28; y: 28
        width: app.width - 56
        spacing: 16

        RowLayout {
            spacing: 14
            Rectangle {
                width: 52; height: 52; radius: 16
                color: Theme.surface2
                border.width: 1; border.color: Theme.line
                Text { anchors.centerIn: parent; text: "EXE"; color: Theme.fg; font.family: Theme.dots; font.pixelSize: 16; font.weight: Font.Black }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: app.v.name; color: Theme.fg; font.pixelSize: 17; font.weight: Font.DemiBold
                       elide: Text.ElideMiddle; Layout.fillWidth: true }
                Text { text: "Программа для Windows · запуск через Bottles"; color: Theme.muted; font.pixelSize: 12 }
            }
        }

        Rectangle {
            visible: !app.v.ok
            Layout.fillWidth: true
            implicitHeight: warn.implicitHeight + 32
            radius: 16
            color: Theme.soft(Theme.warn, 0.08)
            border.width: 1
            border.color: Theme.soft(Theme.warn, 0.45)
            ColumnLayout {
                id: warn
                x: 16; y: 16
                width: parent.width - 32
                spacing: 10
                Text { text: "Скорее всего, не заработает"; color: Theme.warn; font.pixelSize: 14; font.weight: Font.DemiBold }
                Text { text: app.v.reason; color: Theme.fg; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Flow {
                    visible: app.v.alternatives.length > 0
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "Попробуйте:"; color: Theme.muted; font.pixelSize: 13; height: 30; verticalAlignment: Text.AlignVCenter }
                    Repeater {
                        model: app.v.alternatives
                        Btn { required property var modelData; text: modelData.name; small: true
                              onClicked: { backend.storeSearch(modelData.name); Qt.quit() } }
                    }
                }
            }
        }

        Text {
            visible: app.v.ok && app.j.state === ""
            text: app.v.bottles ? "Программа запустится в среде Windows. Первый запуск может занять минуту."
                                : "Для программ Windows нужен Bottles (около 300 МБ). Он поставится один раз — дальше .exe будут открываться сразу."
            color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }

        DotProgress { visible: app.j.state === "running"; value: app.j.pct; text: app.j.text }
        Text {
            visible: app.j.state === "done" || app.j.state === "error"
            text: app.j.text
            color: app.j.state === "error" ? Theme.bad : Theme.ok
            font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Item { Layout.fillWidth: true }
            Btn { text: "Отмена"; onClicked: Qt.quit() }
            Btn {
                text: app.v.ok ? (app.v.bottles ? "Запустить" : "Установить и запустить") : "Всё равно попробовать"
                primary: app.v.ok
                busy: app.running("exe")
                enabled: app.j.state !== "done"
                onClicked: backend.exeRun(exePath)
            }
        }
    }
}
