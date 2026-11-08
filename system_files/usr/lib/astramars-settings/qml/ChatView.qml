import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Разговор с помощником: сообщения, кнопки-действия под ответами, поле ввода
ColumnLayout {
    id: chat
    property bool compact: false
    property bool waiting: false
    spacing: 12

    ListModel { id: messages }

    function send(text) {
        text = text.trim()
        if (text === "" || waiting) return
        messages.append({role: "user", text: text, buttons: [], error: false})
        waiting = true
        backend.chat(text)
        input.text = ""
        Qt.callLater(function () { list.positionViewAtEnd() })
    }

    Connections {
        target: backend
        function onChatReply(r) {
            chat.waiting = false
            messages.append({role: "assistant", text: r.error ? r.error : r.text, buttons: r.buttons || [], error: !!r.error})
            Qt.callLater(function () { list.positionViewAtEnd() })
        }
    }

    ListView {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 200
        clip: true
        spacing: 10
        model: messages
        ScrollBar.vertical: ScrollBar {}

        header: ColumnLayout {
            width: list.width
            spacing: 10
            visible: messages.count === 0
            height: visible ? implicitHeight + 12 : 0
            Text { text: "Спросите что угодно о компьютере"; color: Theme.fg; font.pixelSize: 15; font.weight: Font.DemiBold }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: ["Почему нет звука?", "Чем заменить Photoshop?", "Мало места на диске", "Как поставить Steam?",
                            "Как перенести файлы с Windows?"]
                    Rectangle {
                        required property var modelData
                        height: 34; radius: 17
                        width: s.implicitWidth + 28
                        color: sm.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Theme.glass
                        border.width: 1; border.color: Theme.line
                        Text { id: s; anchors.centerIn: parent; text: modelData; color: Theme.fg; font.pixelSize: 13 }
                        MouseArea { id: sm; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    onClicked: chat.send(modelData) }
                    }
                }
            }
        }

        delegate: Item {
            id: msg
            required property string role
            required property string text
            required property var buttons
            required property bool error
            width: list.width
            height: bubble.height + (btnRow.visible ? btnRow.height + 8 : 0)

            Rectangle {
                id: bubble
                anchors.right: msg.role === "user" ? parent.right : undefined
                width: Math.min(body.implicitWidth + 32, list.width * 0.86)
                height: body.implicitHeight + 22
                radius: 18
                color: msg.role === "user" ? Theme.accent : msg.error ? Theme.soft(Theme.bad, 0.12) : Theme.surface2
                border.width: msg.role === "user" ? 0 : 1
                border.color: msg.error ? Theme.soft(Theme.bad, 0.5) : Theme.line
                TextEdit {
                    id: body
                    x: 16; y: 11
                    width: Math.min(implicitWidth, list.width * 0.86 - 32)
                    text: msg.text
                    textFormat: TextEdit.MarkdownText
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    color: msg.role === "user" ? "#ffffff" : Theme.fg
                    font.pixelSize: 14
                }
            }
            Flow {
                id: btnRow
                visible: msg.buttons.length > 0
                anchors.top: bubble.bottom
                anchors.topMargin: 8
                width: list.width
                spacing: 8
                Repeater {
                    model: msg.buttons
                    Btn {
                        required property var modelData
                        text: modelData.label
                        small: true
                        primary: true
                        onClicked: backend.runButton(modelData.kind, modelData.target)
                    }
                }
            }
        }
        footer: Item {
            width: list.width
            height: chat.waiting ? 40 : 0
            DotProgress { visible: chat.waiting; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 52
        radius: 26
        color: Theme.surface2
        border.width: 1
        border.color: input.activeFocus ? Theme.soft(Theme.accent, 0.6) : Theme.line
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 7
            spacing: 8
            TextField {
                id: input
                Layout.fillWidth: true
                placeholderText: "Напишите вопрос…"
                placeholderTextColor: Theme.faint
                color: Theme.fg
                font.pixelSize: 14
                background: Item {}
                focus: true
                onAccepted: chat.send(text)
            }
            Btn { text: "↑"; primary: true; small: false; implicitWidth: 38; enabled: input.text.trim() !== "" && !chat.waiting
                  onClicked: chat.send(input.text) }
        }
    }
    RowLayout {
        visible: messages.count > 0
        Text { text: "Помощник может ошибаться — проверяйте важное."; color: Theme.faint; font.pixelSize: 11; Layout.fillWidth: true }
        Btn { text: "Новый разговор"; small: true; onClicked: { messages.clear(); backend.chatReset() } }
    }
}
