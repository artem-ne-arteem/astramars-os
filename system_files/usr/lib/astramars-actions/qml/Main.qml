import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: win
    width: 1120
    height: 800
    minimumWidth: 700
    minimumHeight: 560
    visible: false
    title: "Быстрые действия"
    color: Theme.bg

    function openPanel(name) {
        if (name === "editor") editor.openFor("")
    }

    // Фон: сетка точек
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            ctx.fillStyle = "rgba(255,255,255,0.05)"
            for (let y = 14; y < height; y += 22)
                for (let x = 14; x < width; x += 22)
                    ctx.fillRect(x, y, 1.6, 1.6)
        }
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: scroll.availableWidth
            spacing: 18

            // --- шапка -----------------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.topMargin: 26
                spacing: 2
                RowLayout {
                    spacing: 12
                    Rectangle { width: 12; height: 12; radius: 6; color: Theme.accent; Layout.alignment: Qt.AlignVCenter }
                    Text {
                        text: "ACTIONS"
                        font.family: Theme.dots
                        font.pixelSize: 40
                        font.weight: Font.Bold
                        font.letterSpacing: 4
                        font.variableAxes: ({ "ROND": 100, "wght": 700 })
                        color: Theme.fg
                    }
                }
                Text {
                    text: "Быстрые действия · одно нажатие — и система сама выполнит все шаги"
                    font.pixelSize: 13
                    color: Theme.muted
                }
            }

            // --- готовые действия ----------------------------------------------------
            Text {
                Layout.leftMargin: 32
                text: "ГОТОВЫЕ"
                font.pixelSize: 13
                font.weight: Font.Bold
                font.letterSpacing: 2.5
                color: Theme.muted
            }
            Grid {
                id: builtinGrid
                Layout.fillWidth: true
                Layout.leftMargin: 25
                Layout.rightMargin: 25
                readonly property int cols: Math.max(1, Math.floor((scroll.availableWidth - 50) / 270))
                readonly property real cell: (scroll.availableWidth - 50) / cols
                columns: cols
                Repeater {
                    model: backend.builtins
                    delegate: Item {
                        required property var modelData
                        width: builtinGrid.cell
                        height: 176
                        ActionTile {
                            anchors.fill: parent
                            anchors.margins: 7
                            action: modelData
                            onRunClicked: modelData.confirm ? confirm.ask(modelData) : backend.run(modelData.id)
                            onDetailsClicked: details.show(modelData.id)
                        }
                    }
                }
            }

            // --- мои действия ------------------------------------------------------
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.topMargin: 8
                Text {
                    text: "МОИ"
                    font.pixelSize: 13
                    font.weight: Font.Bold
                    font.letterSpacing: 2.5
                    color: Theme.muted
                }
                Text {
                    Layout.leftMargin: 10
                    text: "свои цепочки команд — каждая строка выполняется по очереди"
                    font.pixelSize: 12
                    color: Theme.faint
                }
            }
            Grid {
                id: customGrid
                Layout.fillWidth: true
                Layout.leftMargin: 25
                Layout.rightMargin: 25
                Layout.bottomMargin: 28
                columns: builtinGrid.cols
                Repeater {
                    model: backend.customs
                    delegate: Item {
                        required property var modelData
                        width: builtinGrid.cell
                        height: 176
                        ActionTile {
                            anchors.fill: parent
                            anchors.margins: 7
                            action: modelData
                            onRunClicked: backend.run(modelData.id)
                            onDetailsClicked: details.show(modelData.id)
                            onEditClicked: editor.openFor(modelData.id)
                        }
                    }
                }
                // Плитка «Создать»
                Item {
                    width: builtinGrid.cell
                    height: 176
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 7
                        radius: 24
                        color: newMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent"
                        border.width: 1.5
                        border.color: Theme.line
                        Column {
                            anchors.centerIn: parent
                            spacing: 10
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 46; height: 46; radius: 23
                                color: Theme.fg
                                Text { anchors.centerIn: parent; text: "+"; font.pixelSize: 28; font.weight: Font.Light; color: Theme.bg }
                            }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Создать действие"; font.pixelSize: 14; font.weight: Font.DemiBold; color: Theme.fg }
                        }
                        MouseArea { id: newMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: editor.openFor("") }
                    }
                }
            }
        }
    }

    // --- общий вид всплывающих окон -------------------------------------------------
    component Sheet: Popup {
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(620, win.width - 48)
        padding: 24
        Overlay.modal: Rectangle { color: "#c0000000" }
        background: Rectangle { color: Theme.surface; radius: 26; border.color: Theme.line }
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
            NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 200; easing.type: Easing.OutCubic }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 120 } }
    }

    component Pill: Rectangle {
        property string text: ""
        property bool primary: true
        property bool danger: false
        signal clicked()
        implicitWidth: pillText.implicitWidth + 40
        implicitHeight: 42
        radius: 21
        color: primary ? (pillMouse.containsMouse ? "#ffffff" : Theme.fg)
             : danger ? (pillMouse.containsMouse ? Qt.rgba(1, 0.23, 0.19, 0.25) : Qt.rgba(1, 0.23, 0.19, 0.12))
             : (pillMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Theme.glass)
        border.width: primary ? 0 : 1
        border.color: danger ? Qt.rgba(1, 0.23, 0.19, 0.4) : Theme.line
        Text {
            id: pillText
            anchors.centerIn: parent
            text: parent.text
            font.pixelSize: 14
            font.weight: Font.DemiBold
            color: parent.primary ? Theme.bg : parent.danger ? Theme.accent : Theme.fg
        }
        MouseArea { id: pillMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: parent.clicked() }
    }

    // --- подтверждение -----------------------------------------------------------------
    Sheet {
        id: confirm
        property var action: ({})
        function ask(a) { action = a; open() }
        contentItem: ColumnLayout {
            spacing: 16
            Text { text: confirm.action.title || ""; font.pixelSize: 20; font.weight: Font.Bold; color: Theme.fg }
            Text { Layout.fillWidth: true; text: confirm.action.confirm || ""; wrapMode: Text.WordWrap; font.pixelSize: 14; color: Theme.muted }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Pill { primary: false; text: "Отмена"; onClicked: confirm.close() }
                Pill { text: "Выполнить"; onClicked: { backend.run(confirm.action.id); confirm.close() } }
            }
        }
    }

    // --- подробности -------------------------------------------------------------------
    Sheet {
        id: details
        property var info: ({})
        function show(id) { info = backend.details(id); open() }
        height: Math.min(560, win.height - 80)
        contentItem: ColumnLayout {
            spacing: 14
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: details.info.title || ""; elide: Text.ElideRight; font.pixelSize: 20; font.weight: Font.Bold; color: Theme.fg }
                Rectangle {
                    Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17
                    color: closeMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                    Image { anchors.centerIn: parent; source: "assets/close.svg"; sourceSize: Qt.size(36, 36); width: 18; height: 18 }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: details.close() }
                }
            }
            Text {
                Layout.fillWidth: true
                text: details.info.summary || ""
                visible: text !== ""
                wrapMode: Text.WordWrap
                font.pixelSize: 14
                color: details.info.status === "failed" ? Theme.accent : Theme.fg
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 16
                color: "#050505"
                border.color: Theme.line
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 14
                    TextArea {
                        readOnly: true
                        text: details.info.log || ""
                        wrapMode: TextArea.WrapAnywhere
                        font.family: "JetBrains Mono"
                        font.pixelSize: 12
                        color: "#d8d8d8"
                        selectByMouse: true
                        selectionColor: Theme.accent
                        background: null
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Pill { primary: false; text: "Скопировать"; onClicked: backend.copyText((details.info.summary || "") + "\n\n" + (details.info.log || "")) }
                Pill { text: "Закрыть"; onClicked: details.close() }
            }
        }
    }

    // --- редактор своего действия ------------------------------------------------------
    Sheet {
        id: editor
        property string editId: ""
        property bool asRoot: false
        function openFor(id) {
            const c = id ? backend.custom(id) : { title: "", commands: "", root: false }
            editId = id
            nameField.text = c.title
            commandsField.text = c.commands
            asRoot = c.root
            open()
            nameField.forceActiveFocus()
        }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: editor.editId ? "Изменить действие" : "Новое действие"; font.pixelSize: 20; font.weight: Font.Bold; color: Theme.fg }

            TextField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: "Название, например «Утренний старт»"
                placeholderTextColor: Theme.faint
                color: Theme.fg
                font.pixelSize: 15
                padding: 12
                selectByMouse: true
                background: Rectangle { radius: 14; color: "#050505"; border.color: nameField.activeFocus ? Qt.rgba(1, 1, 1, 0.35) : Theme.line }
            }
            Text { text: "Команды — по одной в строке, выполняются по очереди. Строки с # пропускаются."; font.pixelSize: 12; color: Theme.muted }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 190
                TextArea {
                    id: commandsField
                    placeholderText: "flatpak update -y\nflatpak run org.telegram.desktop &\nnotify-send \"Готово\""
                    placeholderTextColor: Theme.faint
                    color: Theme.fg
                    font.family: "JetBrains Mono"
                    font.pixelSize: 13
                    wrapMode: TextArea.WrapAnywhere
                    selectByMouse: true
                    selectionColor: Theme.accent
                    padding: 12
                    background: Rectangle { radius: 14; color: "#050505"; border.color: commandsField.activeFocus ? Qt.rgba(1, 1, 1, 0.35) : Theme.line }
                }
            }
            // Права администратора
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    implicitWidth: 46; implicitHeight: 26; radius: 13
                    color: editor.asRoot ? Theme.accent : Theme.line
                    Rectangle { width: 20; height: 20; radius: 10; y: 3; x: editor.asRoot ? 23 : 3; color: "#ffffff"; Behavior on x { NumberAnimation { duration: 160 } } }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: editor.asRoot = !editor.asRoot }
                }
                ColumnLayout {
                    spacing: 1
                    Text { text: "От имени администратора"; font.pixelSize: 14; color: Theme.fg }
                    Text { text: "Система спросит пароль перед каждой командой"; font.pixelSize: 12; color: Theme.muted }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Pill { visible: editor.editId !== ""; primary: false; danger: true; text: "Удалить"; onClicked: { backend.deleteCustom(editor.editId); editor.close() } }
                Item { Layout.fillWidth: true }
                Pill { primary: false; text: "Отмена"; onClicked: editor.close() }
                Pill { text: "Сохранить"; onClicked: { backend.saveCustom(editor.editId, nameField.text, commandsField.text, editor.asRoot); editor.close() } }
            }
        }
    }

    // --- уведомление -------------------------------------------------------------------
    Rectangle {
        id: toast
        property string message: ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: opacity > 0 ? 26 : 8
        width: Math.min(toastText.implicitWidth + 40, win.width - 64)
        height: toastText.implicitHeight + 24
        radius: height / 2
        color: Theme.surface2
        border.color: Theme.line
        opacity: 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 220 } }
        Behavior on anchors.bottomMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        Text {
            id: toastText
            anchors.centerIn: parent
            width: Math.min(implicitWidth, win.width - 104)
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            text: toast.message
            font.pixelSize: 14
            color: Theme.fg
        }
        Timer { id: toastTimer; interval: 4500; onTriggered: toast.opacity = 0 }
    }
    Connections {
        target: backend
        function onToast(message) {
            toast.message = message
            toast.opacity = 1
            toastTimer.restart()
        }
    }
}
