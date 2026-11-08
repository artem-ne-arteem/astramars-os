import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Настройки AstraMars: слева список разделов, справа выбранный раздел
ApplicationWindow {
    id: app
    width: 1140
    height: 760
    minimumWidth: 900
    minimumHeight: 560
    visible: false
    title: "Настройки AstraMars"
    color: Theme.bg

    property string page: initialPage || "home"
    // Ход фоновых задач: id → {state, pct, text}
    property var jobs: ({})
    readonly property var sections: [
        {id: "home", title: "Главная", group: ""},
        {id: "appearance", title: "Оформление", group: ""},
        {id: "network", title: "Сеть и VPN", group: ""},
        {id: "system", title: "Система", group: ""},
        {id: "windows", title: "Переезд с Windows", group: "Возможности"},
        {id: "games", title: "Игры", group: "Возможности"},
        {id: "phone", title: "Телефон", group: "Возможности"},
        {id: "assistant", title: "Помощник", group: "Возможности"},
        {id: "laptop", title: "Ноутбук", group: "Устройство"},
        {id: "privacy", title: "Приватность", group: "Устройство"}
    ]

    function openPage(p) { page = p; show(); raise(); requestActivate() }
    function job(id) { return jobs[id] || ({state: "", pct: -1, text: ""}) }
    function running(id) { return job(id).state === "running" }

    Connections {
        target: backend
        function onJob(id, state, pct, text) {
            var j = Object.assign({}, app.jobs)
            j[id] = {state: state, pct: pct, text: text}
            app.jobs = j
            if (state === "done" && text !== "") toast.show(text, false)
            if (state === "error") toast.show(text, true)
        }
        function onOpenPage(p) { app.openPage(p) }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // --- Боковая панель ---------------------------------------------------------
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 260
            color: Theme.side
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.line }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                anchors.topMargin: 22
                spacing: 4

                RowLayout {
                    spacing: 12
                    Layout.bottomMargin: 18
                    Layout.leftMargin: 6
                    Image {
                        source: logoUrl
                        sourceSize: Qt.size(88, 88)
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        smooth: true
                    }
                    ColumnLayout {
                        spacing: 0
                        Text { text: "SETTINGS"; color: Theme.fg; font.family: Theme.dots; font.pixelSize: 22; font.weight: Font.Black }
                        RowLayout {
                            spacing: 6
                            Rectangle { width: 6; height: 6; radius: 3; color: Theme.accent }
                            Text { text: "AstraMars OS"; color: Theme.muted; font.pixelSize: 12 }
                        }
                    }
                }

                Repeater {
                    model: app.sections
                    ColumnLayout {
                        id: navItem
                        required property var modelData
                        required property int index
                        readonly property bool on: app.page === modelData.id
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            visible: navItem.modelData.group !== "" &&
                                     (navItem.index === 0 || app.sections[navItem.index - 1].group !== navItem.modelData.group)
                            text: navItem.modelData.group.toUpperCase()
                            color: Theme.faint
                            font.pixelSize: 11
                            font.letterSpacing: 1.2
                            font.weight: Font.DemiBold
                            Layout.topMargin: 14
                            Layout.leftMargin: 12
                            Layout.bottomMargin: 2
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            radius: 20
                            color: navItem.on ? Theme.surface2 : navMouse.containsMouse ? Theme.surface : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 12
                                Text {
                                    text: (navItem.index + 1 < 10 ? "0" : "") + (navItem.index + 1)
                                    color: navItem.on ? Theme.accent : Theme.faint
                                    font.family: Theme.dots
                                    font.pixelSize: 15
                                    font.weight: Font.Black
                                }
                                Text {
                                    text: navItem.modelData.title
                                    color: navItem.on ? Theme.fg : "#c8c8c8"
                                    font.pixelSize: 14
                                    font.weight: navItem.on ? Font.DemiBold : Font.Normal
                                    Layout.fillWidth: true
                                }
                                Rectangle {
                                    visible: navItem.on
                                    width: 6; height: 6; radius: 3
                                    color: Theme.accent
                                }
                            }
                            MouseArea {
                                id: navMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: app.page = navItem.modelData.id
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    radius: 20
                    color: kdeMouse.containsMouse ? Theme.surface : "transparent"
                    border.width: 1
                    border.color: Theme.line
                    Text {
                        anchors.centerIn: parent
                        text: "Все настройки KDE  →"
                        color: Theme.muted
                        font.pixelSize: 13
                    }
                    MouseArea {
                        id: kdeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: backend.openKde("")
                    }
                }
            }
        }

        // --- Раздел ------------------------------------------------------------------------
        Loader {
            id: pageLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            source: "pages/" + app.page.charAt(0).toUpperCase() + app.page.slice(1) + "Page.qml"
            opacity: status === Loader.Ready ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 160 } }
        }
    }

    // --- Всплывающее сообщение внизу ------------------------------------------------------
    Rectangle {
        id: toast
        property bool error: false
        function show(text, isError) {
            toastText.text = text
            error = isError
            opacity = 1
            hideTimer.restart()
        }
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: 130
        anchors.bottom: parent.bottom
        anchors.bottomMargin: opacity > 0 ? 26 : 10
        Behavior on anchors.bottomMargin { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
        width: Math.min(toastText.implicitWidth + 64, app.width - 360)
        height: Math.max(46, toastText.implicitHeight + 24)
        radius: 23
        color: "#161616"
        border.width: 1
        border.color: error ? Theme.soft(Theme.bad, 0.6) : Theme.line
        opacity: 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            spacing: 10
            Rectangle { width: 8; height: 8; radius: 4; color: toast.error ? Theme.bad : Theme.accent }
            Text {
                id: toastText
                color: Theme.fg
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
        Timer { id: hideTimer; interval: 5200; onTriggered: toast.opacity = 0 }
    }
}
