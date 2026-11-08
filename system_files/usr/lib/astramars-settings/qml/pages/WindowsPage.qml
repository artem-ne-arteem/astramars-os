import QtQuick
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "FROM WINDOWS"
    caption: "Перенесите файлы, закладки и обои с диска Windows. Диск подключается только для чтения — с Windows ничего не случится."

    property var found: null
    property var folders: backend.windowsFolders()
    property var picked: ({desktop: true, documents: true, pictures: true, music: true, videos: true, downloads: false})
    property bool bookmarks: true
    property bool wallpaper: true
    property int sysIndex: 0
    property int userIndex: 0
    readonly property var sys: found && found.systems.length ? found.systems[sysIndex] : null
    readonly property var user: sys ? sys.users[userIndex] : null
    readonly property var job: app.job("migrate")

    Connections {
        target: backend
        function onWindowsFound(r) { root.found = r; root.sysIndex = 0; root.userIndex = 0 }
    }
    Component.onCompleted: backend.windowsScan()

    // --- Поиск ------------------------------------------------------------------------------------------
    Card {
        visible: !root.sys
        title: app.running("winscan") ? "Ищу диск Windows…" : "Диск Windows не найден"
        subtitle: app.running("winscan") ? "" : root.found && root.found.errors.length ? root.found.errors.join("\n")
                  : "Если Windows стоит на этом компьютере, проверьте, что диск не зашифрован BitLocker."
        DotProgress { visible: app.running("winscan") }
        Btn { visible: !app.running("winscan"); text: "Искать снова"; small: true; onClicked: backend.windowsScan() }
    }

    // --- Что переносить -------------------------------------------------------------------------------
    Card {
        visible: !!root.sys
        title: root.sys ? "Найдена Windows · " + root.sys.label + " · " + root.sys.size : ""
        subtitle: "Выберите пользователя Windows и что перенести. Файлы попадут в ваши папки, в подпапку «Из Windows»."

        Seg {
            visible: root.sys && root.sys.users.length > 1
            model: root.sys ? root.sys.users.map(function (u, i) { return {id: String(i), name: u.name} }) : []
            current: String(root.userIndex)
            onPicked: function (id) { root.userIndex = parseInt(id) }
        }
        Text { visible: root.sys && root.sys.users.length === 1; text: root.user ? "Пользователь: " + root.user.name : ""
               color: Theme.muted; font.pixelSize: 13 }

        GridLayout {
            Layout.fillWidth: true
            columns: 3
            columnSpacing: 10
            rowSpacing: 10
            Repeater {
                model: root.folders
                Rectangle {
                    id: f
                    required property var modelData
                    readonly property bool on: !!root.picked[modelData.id]
                    Layout.fillWidth: true
                    implicitHeight: 48
                    radius: 14
                    color: on ? Theme.soft(Theme.accent, 0.1) : Theme.surface2
                    border.width: 1
                    border.color: on ? Theme.soft(Theme.accent, 0.5) : Theme.line
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        Rectangle {
                            width: 18; height: 18; radius: 6
                            color: f.on ? Theme.accent : "transparent"
                            border.width: f.on ? 0 : 2
                            border.color: Theme.faint
                            Text { anchors.centerIn: parent; text: "✓"; color: "#fff"; font.pixelSize: 12; visible: f.on }
                        }
                        Text { text: f.modelData.title; color: Theme.fg; font.pixelSize: 14; Layout.fillWidth: true }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: { var p = Object.assign({}, root.picked); p[f.modelData.id] = !f.on; root.picked = p }
                    }
                }
            }
        }
        SettingRow {
            title: "Закладки браузеров"
            subtitle: "Chrome, Edge, Яндекс, Opera, Brave, Firefox → один файл для импорта. Пароли Windows не отдаёт — " +
                      "экспортируйте их в браузере на Windows."
            Toggle { checked: root.bookmarks; onToggled: function (v) { root.bookmarks = v } }
        }
        SettingRow {
            title: "Обои рабочего стола"
            Toggle { checked: root.wallpaper; onToggled: function (v) { root.wallpaper = v } }
        }

        DotProgress {
            visible: root.job.state === "running"
            value: root.job.pct
            text: root.job.text
        }
        Text {
            visible: root.job.state === "done" || root.job.state === "error"
            text: root.job.text
            color: root.job.state === "error" ? Theme.bad : Theme.ok
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        RowLayout {
            spacing: 10
            Btn {
                text: root.job.state === "running" ? "Переношу…" : "Перенести"
                primary: true
                busy: root.job.state === "running"
                onClicked: backend.migrate(root.user.path,
                                           root.folders.filter(function (x) { return root.picked[x.id] }).map(function (x) { return x.id }),
                                           root.bookmarks, root.wallpaper)
            }
            Btn { visible: root.job.state === "running"; text: "Остановить"; small: true; onClicked: backend.cancel("migrate") }
            Btn { visible: root.job.state === "done"; text: "Открыть «Из Windows»"; onClicked: backend.openPath(backend.migratedFolder()) }
        }
    }

    Card {
        visible: !!root.sys
        title: "Диск Windows в «Файлах»"
        SettingRow {
            title: "Подключать при каждом входе"
            subtitle: "Только для чтения: файлы Windows видно и можно копировать"
            Toggle {
                id: autoToggle
                checked: root.found ? root.found.automount : false
                onToggled: function (v) { backend.setWindowsAutomount(root.sys.uuid, v); checked = v }
            }
        }
        Btn { text: "Открыть диск Windows"; small: true; onClicked: backend.openPath(root.sys.root) }
    }

    Card {
        title: "Программы для Windows"
        subtitle: "Файлы .exe и .msi открываются двойным щелчком: AstraMars сама поставит Bottles и подготовит среду. " +
                  "Если программа точно не заработает (игры с защитой от читов, Adobe, новый Office), мы скажем об этом и предложим замену."
        RowLayout {
            spacing: 10
            Btn { text: "Открыть Bottles"; onClicked: backend.openBottles() }
            Btn { text: "Замены программ Windows"; onClicked: backend.storeSearch("") }
        }
    }
}
