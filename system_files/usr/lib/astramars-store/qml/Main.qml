import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: win
    width: 1180
    height: 780
    minimumWidth: 760
    minimumHeight: 560
    visible: false
    title: "AstraMars Store"
    color: Theme.bg

    // Фон: еле заметная сетка точек, как на обоях экрана входа
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

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 32
        anchors.rightMargin: 32
        anchors.topMargin: 26
        anchors.bottomMargin: 18
        spacing: 18

        // --- шапка ---------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: 18

            ColumnLayout {
                spacing: 2
                RowLayout {
                    spacing: 12
                    Rectangle { width: 12; height: 12; radius: 6; color: Theme.accent; Layout.alignment: Qt.AlignVCenter }
                    Text {
                        text: "STORE"
                        font.family: Theme.dots
                        font.pixelSize: 40
                        font.weight: Font.Bold
                        font.letterSpacing: 4
                        font.variableAxes: ({ "ROND": 100, "wght": 700 })
                        color: Theme.fg
                    }
                }
                Text {
                    text: backend.loading ? "Загружаю каталог Flathub…"
                        : "AstraMars Store · " + backend.catalogSize + " приложений · установка одной кнопкой"
                    font.pixelSize: 13
                    color: Theme.muted
                }
            }

            Item { Layout.fillWidth: true }

            // Поиск по всему Flathub
            Rectangle {
                Layout.preferredWidth: Math.min(380, win.width * 0.36)
                Layout.preferredHeight: 46
                radius: 23
                color: Theme.glass
                border.width: 1
                border.color: search.activeFocus ? Qt.rgba(1, 1, 1, 0.35) : Theme.line
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 8
                    spacing: 10
                    Image { source: "assets/search.svg"; sourceSize: Qt.size(36, 36); Layout.preferredWidth: 18; Layout.preferredHeight: 18 }
                    TextField {
                        id: search
                        Layout.fillWidth: true
                        placeholderText: "Найти приложение"
                        placeholderTextColor: Theme.faint
                        color: Theme.fg
                        font.pixelSize: 15
                        selectByMouse: true
                        selectionColor: Theme.accent
                        background: null
                        onTextChanged: searchDelay.restart()
                        Keys.onEscapePressed: text = ""
                        Timer { id: searchDelay; interval: 220; onTriggered: backend.setQuery(search.text) }
                    }
                    Rectangle {
                        visible: search.text !== ""
                        Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15
                        color: clearMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.1) : "transparent"
                        Image { anchors.centerIn: parent; source: "assets/close.svg"; sourceSize: Qt.size(32, 32); width: 16; height: 16 }
                        MouseArea { id: clearMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: search.text = "" }
                    }
                }
            }
        }

        // --- разделы -------------------------------------------------------------
        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            contentWidth: chips.implicitWidth
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Row {
                id: chips
                spacing: 8
                Repeater {
                    model: backend.categories
                    delegate: Chip {
                        required property var modelData
                        text: modelData.title
                        active: backend.category === modelData.key
                        onClicked: {
                            search.text = ""
                            backend.setCategory(modelData.key)
                        }
                    }
                }
            }
        }

        Text {
            text: backend.title.toUpperCase()
            font.pixelSize: 13
            font.weight: Font.Bold
            font.letterSpacing: 2.5
            color: Theme.muted
        }

        // --- сетка приложений ------------------------------------------------------
        GridView {
            id: grid
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: backend.model
            readonly property int columns: Math.max(1, Math.floor(width / 330))
            cellWidth: Math.floor(width / columns)
            cellHeight: 178
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                required property string appId
                required property string name
                required property string summary
                required property string icon
                required property string developer
                required property string status
                required property int progress
                width: grid.cellWidth
                height: grid.cellHeight
                AppCard {
                    anchors.fill: parent
                    anchors.margins: 7
                    appId: parent.appId
                    name: parent.name
                    summary: parent.summary
                    icon: parent.icon
                    developer: parent.developer
                    state_: parent.status
                    progress: parent.progress
                    onInstallClicked: backend.install(appId)
                    onOpenClicked: backend.launch(appId)
                    onRemoveClicked: backend.remove(appId)
                }
            }

            Column {
                anchors.centerIn: parent
                spacing: 10
                visible: grid.count === 0
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: backend.loading ? "· · ·" : backend.category === "search" ? "Ничего не нашлось"
                        : backend.category === "installed" ? "Здесь появятся установленные приложения" : "Раздел пуст"
                    font.family: backend.loading ? Theme.dots : ""
                    font.pixelSize: backend.loading ? 40 : 16
                    color: Theme.muted
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: backend.loading
                    text: "Загружаю каталог Flathub"
                    font.pixelSize: 13
                    color: Theme.faint
                }
            }
        }
    }

    // --- уведомление ---------------------------------------------------------------
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
        Timer { id: toastTimer; interval: 4000; onTriggered: toast.opacity = 0 }
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
