import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var a: backend.assistantInfo()
    property bool editKey: false
    Connections {
        target: backend
        function onChanged(what) { if (what === "assistant") { root.a = backend.assistantInfo(); root.editKey = false } }
    }

    ColumnLayout {
        x: 36; y: 28
        width: Math.max(320, Math.min(root.width - 72, 880))
        height: root.height - 56
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Text { text: "ASSISTANT"; color: Theme.fg; font.family: Theme.dots; font.pixelSize: 40; font.weight: Font.Black
                   Layout.fillWidth: true }
            Text { text: "Meta + A — из любого места"; color: Theme.muted; font.pixelSize: 12 }
        }
        Text {
            text: "Помощник на Claude объясняет, советует и показывает кнопки: починить звук, освободить место, найти программу. " +
                  "Сам он ничего не запускает — только вы."
            color: Theme.muted; font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }

        // --- Ключ API ------------------------------------------------------------------------------
        Card {
            title: root.a.hasKey ? "Ключ Anthropic API добавлен " + root.a.keyHint : "Нужен ключ Anthropic API"
            subtitle: root.a.hasKey ? "Модель " + root.a.model + ". Из России API работает через VPN."
                      : "Без ключа помощник понимает только простые просьбы. Ключ создаётся на console.anthropic.com → API Keys " +
                        "(оплата по использованию). Хранится только на этом компьютере."
            RowLayout {
                visible: !root.a.hasKey || root.editKey
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 40
                    radius: 20
                    color: Theme.surface2
                    border.width: 1
                    border.color: keyField.activeFocus ? Theme.soft(Theme.accent, 0.6) : Theme.line
                    TextField {
                        id: keyField
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        echoMode: TextInput.Password
                        placeholderText: "sk-ant-…"
                        placeholderTextColor: Theme.faint
                        color: Theme.fg
                        font.pixelSize: 13
                        background: Item {}
                        onAccepted: if (text.trim() !== "") backend.setApiKey(text)
                    }
                }
                Btn { text: "Сохранить"; primary: true; enabled: keyField.text.trim() !== ""; onClicked: backend.setApiKey(keyField.text) }
                Btn { text: "Ключ на сайте"; onClicked: Qt.openUrlExternally("https://console.anthropic.com/settings/keys") }
            }
            RowLayout {
                visible: root.a.hasKey && !root.editKey
                spacing: 10
                Btn { text: "Заменить ключ"; small: true; onClicked: root.editKey = true }
                Btn { text: "Удалить ключ"; small: true; danger: true; onClicked: backend.setApiKey("") }
            }
        }

        // --- Разговор ---------------------------------------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 280
            radius: 22
            color: Theme.surface
            border.width: 1
            border.color: Theme.line
            ChatView {
                anchors.fill: parent
                anchors.margins: 18
            }
        }
    }
}
