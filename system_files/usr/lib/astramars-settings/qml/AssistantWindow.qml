import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Отдельное окно помощника (Meta + A): только разговор
ApplicationWindow {
    id: app
    width: 560
    height: 720
    minimumWidth: 420
    minimumHeight: 480
    visible: false
    title: "Помощник AstraMars"
    color: Theme.bg
    property var jobs: ({})
    function job(id) { return ({state: "", pct: -1, text: ""}) }
    function running(id) { return false }
    property var info: backend.assistantInfo()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Image { source: logoUrl; sourceSize: Qt.size(72, 72); Layout.preferredWidth: 34; Layout.preferredHeight: 34 }
            ColumnLayout {
                spacing: 0
                Layout.fillWidth: true
                Text { text: "ASSISTANT"; color: Theme.fg; font.family: Theme.dots; font.pixelSize: 22; font.weight: Font.Black }
                RowLayout {
                    spacing: 6
                    Rectangle { width: 6; height: 6; radius: 3; color: app.info.hasKey ? Theme.accent : Theme.faint }
                    Text { text: app.info.hasKey ? "Claude · отвечает на любые вопросы" : "Простой режим — добавьте ключ API"
                           color: Theme.muted; font.pixelSize: 12 }
                }
            }
            Btn { visible: !app.info.hasKey; text: "Ключ API"; small: true; onClicked: backend.runButton("settings_page", "assistant") }
        }
        ChatView { Layout.fillWidth: true; Layout.fillHeight: true }
    }
}
