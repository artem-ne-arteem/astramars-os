import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: win
    width: 420
    height: 800
    minimumWidth: 380
    minimumHeight: 660
    visible: false
    title: "AstraMars VPN"
    color: Theme.bg

    property bool hideOnClose: false
    onClosing: (close) => {
        if (hideOnClose) {
            close.accepted = false
            win.hide()
        }
    }

    readonly property string status: backend.status
    readonly property bool isOn: status === "on"

    function openPanel(name) {
        if (name === "add") addPopup.open()
        else if (name === "settings") settingsPopup.open()
    }

    // --- фон: звёзды и тёплое свечение -----------------------------------------
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const g = ctx.createRadialGradient(width / 2, 300, 0, width / 2, 300, width * 0.9)
            g.addColorStop(0, "rgba(255,122,69,0.10)")
            g.addColorStop(1, "rgba(255,122,69,0)")
            ctx.fillStyle = g
            ctx.fillRect(0, 0, width, height)
            let seed = 11
            const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 }
            for (let i = 0; i < 80; i++) {
                ctx.fillStyle = "rgba(255,255,255," + (0.12 + rnd() * 0.45).toFixed(2) + ")"
                ctx.beginPath()
                ctx.arc(rnd() * width, rnd() * height, 0.3 + rnd() * 1.2, 0, Math.PI * 2)
                ctx.fill()
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        anchors.topMargin: 18
        anchors.bottomMargin: 16
        spacing: 14

        // --- шапка ---------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Image {
                source: "assets/logo.svg"
                sourceSize: Qt.size(72, 72)
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Text {
                    text: "AstraMars VPN"
                    font.pixelSize: 17
                    font.weight: Font.Bold
                    color: Theme.fg
                }
                Text {
                    Layout.fillWidth: true
                    text: backend.current.name ? backend.current.protocol + " · " + backend.current.name : "Сервер не выбран"
                    elide: Text.ElideRight
                    font.pixelSize: 12
                    color: Theme.muted
                }
            }
            IconButton {
                icon: "gear"
                tip: "Настройки"
                onClicked: settingsPopup.open()
            }
        }

        ModeSwitch {
            Layout.fillWidth: true
            mode: backend.mode
            onPicked: (m) => backend.setMode(m)
        }

        // --- кнопка-планета и статус ------------------------------------------------
        ConnectOrb {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 2
            status: win.status
            onClicked: backend.toggleConnection()
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: -6
            spacing: 4
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: win.status === "on" ? (backend.mode === "tun" ? "Защищено" : "Прокси работает")
                    : win.status === "connecting" ? "Подключение…"
                    : win.status === "error" ? "Не удалось подключиться"
                    : "Не подключено"
                font.pixelSize: 21
                font.weight: Font.DemiBold
                color: win.status === "error" ? Theme.danger : Theme.fg
            }
            Text {
                id: subline
                Layout.fillWidth: true
                Layout.leftMargin: 10
                Layout.rightMargin: 10
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                property int tick: 0
                text: {
                    tick
                    if (win.isOn) {
                        const s = Math.max(0, Math.floor((Date.now() - backend.connectedSince) / 1000))
                        const pad = (n) => String(n).padStart(2, "0")
                        const t = pad(Math.floor(s / 3600)) + ":" + pad(Math.floor(s / 60) % 60) + ":" + pad(s % 60)
                        return backend.mode === "tun" ? t : t + " · 127.0.0.1:2080"
                    }
                    if (win.status === "error") return backend.error
                    if (win.status === "connecting") return "Запускаю ядро sing-box"
                    return backend.servers.length ? "Нажмите на планету, чтобы подключиться" : "Добавьте сервер, чтобы начать"
                }
                font.family: win.isOn ? Theme.mono : ""
                font.pixelSize: 13
                color: Theme.muted
                Timer {
                    interval: 1000
                    repeat: true
                    running: win.isOn && win.visible
                    onTriggered: subline.tick++
                }
            }

            // Скорость
            Item {
                Layout.fillWidth: true
                Layout.topMargin: 6
                implicitHeight: speeds.implicitHeight
            Row {
                id: speeds
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 10
                opacity: win.isOn ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 300 } }
                Repeater {
                    model: [
                        { arrow: "↓", value: backend.downSpeed, tint: Theme.ok },
                        { arrow: "↑", value: backend.upSpeed, tint: Theme.astra }
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: 118
                        height: 32
                        radius: 16
                        color: Theme.surface
                        border.color: Theme.line
                        Row {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: modelData.arrow; color: modelData.tint; font.pixelSize: 14; font.weight: Font.Bold }
                            Text { text: modelData.value; color: Theme.fg; font.family: Theme.mono; font.pixelSize: 12 }
                        }
                    }
                }
            }
            }
        }

        // --- серверы -----------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 4
            spacing: 2
            Text {
                text: "Серверы"
                font.pixelSize: 15
                font.weight: Font.DemiBold
                color: Theme.fg
            }
            Text {
                Layout.leftMargin: 6
                text: backend.servers.length
                font.family: Theme.mono
                font.pixelSize: 12
                color: Theme.faint
            }
            Item { Layout.fillWidth: true }
            IconButton { icon: "bolt"; tip: "Проверить пинг"; onClicked: backend.pingAll() }
            IconButton {
                icon: "refresh"; tip: "Обновить подписки"
                spinning: backend.busy
                visible: backend.subscriptions.length > 0
                onClicked: backend.updateSubscriptions()
            }
            IconButton { icon: "plus"; tip: "Добавить сервер или подписку"; onClicked: addPopup.open() }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: backend.servers
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: ServerRow {
                required property var modelData
                width: list.width
                server: modelData
                selected: modelData.id === backend.selected
                onPicked: backend.selectServer(modelData.id)
                onRemoveRequested: backend.removeServer(modelData.id)
            }

            Column {
                anchors.centerIn: parent
                spacing: 14
                visible: list.count === 0
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Здесь появятся ваши серверы"
                    font.pixelSize: 14
                    color: Theme.muted
                }
                PillButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Добавить сервер"
                    onClicked: addPopup.open()
                }
            }
        }
    }

    // --- уведомление ------------------------------------------------------------------
    Rectangle {
        id: toast
        property string message: ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: opacity > 0 ? 20 : 4
        width: Math.min(toastText.implicitWidth + 32, win.width - 40)
        height: toastText.implicitHeight + 22
        radius: 14
        color: Theme.surface2
        border.color: Theme.line
        opacity: 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 220 } }
        Behavior on anchors.bottomMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        Text {
            id: toastText
            anchors.centerIn: parent
            width: Math.min(implicitWidth, win.width - 72)
            text: toast.message
            wrapMode: Text.WordWrap
            font.pixelSize: 13
            color: Theme.fg
        }
        Timer {
            id: toastTimer
            interval: 4500
            onTriggered: toast.opacity = 0
        }
    }
    Connections {
        target: backend
        function onToast(message) {
            toast.message = message
            toast.opacity = 1
            toastTimer.restart()
        }
    }

    // --- окно добавления ----------------------------------------------------------------
    Popup {
        id: addPopup
        modal: true
        focus: true
        anchors.centerIn: Overlay.overlay
        width: win.width - 32
        padding: 20
        onOpened: input.forceActiveFocus()
        Overlay.modal: Rectangle { color: "#b0050409" }
        background: Rectangle { color: Theme.surface; radius: 22; border.color: Theme.line }
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
            NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 200; easing.type: Easing.OutCubic }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 120 } }

        contentItem: ColumnLayout {
            spacing: 14
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Добавить сервер"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    color: Theme.fg
                }
                IconButton { icon: "close"; onClicked: addPopup.close() }
            }
            Text {
                Layout.fillWidth: true
                text: "Вставьте ссылки (по одной на строку) или адрес подписки https://…"
                wrapMode: Text.WordWrap
                font.pixelSize: 13
                color: Theme.muted
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 150
                TextArea {
                    id: input
                    wrapMode: TextArea.WrapAnywhere
                    color: Theme.fg
                    font.family: Theme.mono
                    font.pixelSize: 12
                    selectByMouse: true
                    selectionColor: Theme.mars
                    placeholderText: "https://sub.example.com/…\nvless://…  vmess://…  trojan://…\nss://…  hy2://…  tuic://…  anytls://…"
                    placeholderTextColor: Theme.faint
                    padding: 12
                    background: Rectangle {
                        color: Theme.bg
                        radius: 14
                        border.color: input.activeFocus ? Theme.mars : Theme.line
                    }
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 6
                Repeater {
                    model: ["VLESS", "Reality", "VMess", "Trojan", "Shadowsocks", "Hysteria2", "TUIC", "AnyTLS", "SOCKS"]
                    delegate: Rectangle {
                        required property string modelData
                        width: chip.implicitWidth + 16
                        height: 22
                        radius: 11
                        color: Theme.surface2
                        Text {
                            id: chip
                            anchors.centerIn: parent
                            text: modelData
                            font.pixelSize: 11
                            color: Theme.muted
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                PillButton {
                    primary: false
                    text: "Из буфера"
                    onClicked: input.text = backend.clipboardText()
                }
                Item { Layout.fillWidth: true }
                PillButton {
                    text: "Добавить"
                    onClicked: {
                        backend.addFromText(input.text)
                        input.text = ""
                        addPopup.close()
                    }
                }
            }
        }
    }

    // --- настройки ---------------------------------------------------------------------
    Popup {
        id: settingsPopup
        modal: true
        anchors.centerIn: Overlay.overlay
        width: win.width - 32
        height: Math.min(implicitHeight, win.height - 48)
        padding: 20
        Overlay.modal: Rectangle { color: "#b0050409" }
        background: Rectangle { color: Theme.surface; radius: 22; border.color: Theme.line }
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 160 }
            NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 200; easing.type: Easing.OutCubic }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 120 } }

        contentItem: Flickable {
            implicitHeight: settingsColumn.implicitHeight
            contentHeight: settingsColumn.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: settingsColumn
                width: parent.width
                spacing: 18

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: "Настройки"
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: Theme.fg
                    }
                    IconButton { icon: "close"; onClicked: settingsPopup.close() }
                }

                SettingRow {
                    Layout.fillWidth: true
                    title: "Российские сайты напрямую"
                    hint: "Госуслуги, банки и сайты .ru открываются без VPN"
                    checked: backend.bypassRu
                    onToggled: (v) => backend.setBypassRu(v)
                }
                SettingRow {
                    Layout.fillWidth: true
                    title: "Подключаться при запуске"
                    hint: "Сразу включать VPN, когда открывается приложение"
                    checked: backend.autoconnect
                    onToggled: (v) => backend.setAutoconnect(v)
                }
                SettingRow {
                    Layout.fillWidth: true
                    title: "Запускать при входе в систему"
                    hint: "Приложение будет ждать в трее"
                    checked: backend.autostart
                    onToggled: (v) => backend.setAutostart(v)
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }

                Text {
                    text: "Подписки"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    color: Theme.fg
                }
                Text {
                    visible: backend.subscriptions.length === 0
                    Layout.fillWidth: true
                    text: "Добавьте адрес подписки через «+» на главном экране"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                    color: Theme.muted
                }
                Repeater {
                    model: backend.subscriptions
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: subCol.implicitHeight + 24
                        radius: 14
                        color: Theme.bg
                        border.color: Theme.line
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8
                            ColumnLayout {
                                id: subCol
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 6
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    elide: Text.ElideRight
                                    font.pixelSize: 14
                                    color: Theme.fg
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.details
                                    elide: Text.ElideRight
                                    font.pixelSize: 12
                                    color: Theme.muted
                                }
                                Rectangle {
                                    visible: modelData.usage >= 0
                                    Layout.fillWidth: true
                                    height: 4
                                    radius: 2
                                    color: Theme.line
                                    Rectangle {
                                        width: parent.width * Math.min(1, Math.max(0, modelData.usage))
                                        height: parent.height
                                        radius: 2
                                        color: modelData.usage > 0.9 ? Theme.danger : Theme.mars
                                    }
                                }
                            }
                            IconButton {
                                icon: "trash"
                                tip: "Удалить подписку и её серверы"
                                onClicked: backend.removeSubscription(modelData.id)
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    text: backend.version
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 11
                    color: Theme.faint
                }
            }
        }
    }
}
