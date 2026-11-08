import QtQuick
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "NETWORK"
    caption: "Проверьте, что открывается, выберите DNS и включите VPN — всё в одном месте."

    property var sites: backend.sites()
    property var results: ({})
    property var vpn: backend.vpnState()
    property string dns: backend.dnsCurrent()
    property var presets: backend.dnsPresets()
    readonly property int checked: Object.keys(results).length
    readonly property int bad: Object.keys(results).filter(function (k) { return !results[k].ok }).length

    Connections {
        target: backend
        function onSiteResult(r) { var x = Object.assign({}, root.results); x[r.id] = r; root.results = x }
        function onChanged(what) { if (what === "dns") root.dns = backend.dnsCurrent() }
    }
    Component.onCompleted: { if (!app.running("sites")) backend.checkSites() }

    // --- VPN ---------------------------------------------------------------------------------------
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 96
        radius: 22
        color: root.vpn.vpn ? Theme.soft(Theme.ok, 0.08) : Theme.surface
        border.width: 1
        border.color: root.vpn.vpn ? Theme.soft(Theme.ok, 0.4) : Theme.line
        RowLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16
            Rectangle {
                width: 52; height: 52; radius: 26
                color: root.vpn.vpn ? Theme.ok : Theme.surface2
                Text { anchors.centerIn: parent; text: "VPN"; color: root.vpn.vpn ? "#000" : Theme.muted
                       font.family: Theme.dots; font.pixelSize: 15; font.weight: Font.Black }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text { text: root.vpn.vpn ? "Ygolek VPN включён" : "Ygolek VPN выключен"; color: Theme.fg
                       font.pixelSize: 17; font.weight: Font.DemiBold }
                Text {
                    text: root.vpn.proxy ? "Системный прокси: " + root.vpn.proxy
                                         : "YouTube, Discord и другие сайты из мира открываются через VPN, российские — напрямую"
                    color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
                }
            }
            Btn { text: root.vpn.vpn ? "Открыть" : "Включить"; primary: !root.vpn.vpn; visible: root.vpn.installed
                  onClicked: backend.openVpn() }
        }
    }

    // --- Проверка доступа ----------------------------------------------------------------------------
    Card {
        title: "Что открывается"
        subtitle: app.running("sites") ? "Проверяю… " + root.checked + " из " + root.sites.length
                : root.checked === 0 ? "" : root.bad === 0 ? "Всё открывается" :
                  "Не открывается: " + root.bad + (root.vpn.vpn ? "" : " — включите VPN")
        badge: root.bad > 0 && !app.running("sites") && !root.vpn.vpn ? "нужен VPN" : ""

        Repeater {
            model: [["world", "Мир"], ["ru", "Россия"]]
            ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 8
                Text { text: modelData[1].toUpperCase(); color: Theme.faint; font.pixelSize: 11; font.letterSpacing: 1.2 }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    Repeater {
                        model: root.sites.filter(function (s) { return s.group === modelData[0] })
                        Rectangle {
                            id: tile
                            required property var modelData
                            readonly property var r: root.results[modelData.id]
                            width: 196; height: 44; radius: 14
                            color: Theme.surface2
                            border.width: 1
                            border.color: r && !r.ok ? Theme.soft(Theme.bad, 0.45) : Theme.line
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 10
                                StatusDot { kind: tile.r ? (tile.r.ok ? "ok" : "bad") : ""; pulse: !tile.r && app.running("sites") }
                                Text { text: tile.modelData.name; color: Theme.fg; font.pixelSize: 13; Layout.fillWidth: true }
                                Text {
                                    text: tile.r ? (tile.r.ok ? tile.r.ms + " мс" : tile.r.note) : ""
                                    color: tile.r && !tile.r.ok ? Theme.bad : Theme.muted
                                    font.pixelSize: 11
                                    font.family: Theme.mono
                                }
                            }
                        }
                    }
                }
            }
        }
        Btn { text: "Проверить снова"; small: true; busy: app.running("sites")
              onClicked: { root.results = ({}); backend.checkSites() } }
    }

    // --- DNS ------------------------------------------------------------------------------------------
    Card {
        title: "DNS"
        subtitle: "Через какой сервер компьютер узнаёт адреса сайтов. Запросы шифруются, если сервер это умеет."
        Repeater {
            model: root.presets
            Rectangle {
                id: opt
                required property var modelData
                readonly property bool on: root.dns === modelData.id
                Layout.fillWidth: true
                implicitHeight: 52
                radius: 14
                color: on ? Theme.soft(Theme.accent, 0.1) : dnsMouse.containsMouse ? Theme.surfaceHover : "transparent"
                border.width: 1
                border.color: on ? Theme.soft(Theme.accent, 0.5) : Theme.line
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 12
                    Rectangle {
                        width: 18; height: 18; radius: 9
                        color: "transparent"
                        border.width: 2
                        border.color: opt.on ? Theme.accent : Theme.faint
                        Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: Theme.accent; visible: opt.on }
                    }
                    Text { text: opt.modelData.name; color: Theme.fg; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Text { text: opt.modelData.hint; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                MouseArea { id: dnsMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            enabled: !app.running("dns"); onClicked: backend.setDns(opt.modelData.id) }
            }
        }
        DotProgress { visible: app.running("dns"); text: "Применяю DNS…" }
    }

    Btn { text: "Wi-Fi и подключения…"; onClicked: backend.openKde("kcm_networkmanagement") }
}
