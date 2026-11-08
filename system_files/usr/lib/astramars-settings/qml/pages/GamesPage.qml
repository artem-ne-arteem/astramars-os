import QtQuick
import QtQuick.Layouts
import ".."

Page {
    id: root
    heading: "GAMES"
    caption: "Steam с Proton запускает большинство игр для Windows. Всё ставится одной кнопкой."

    property var g: backend.gamesInfo()
    readonly property bool kitDone: g.kit.every(function (k) { return k.installed })
    readonly property var kitJob: app.job("kit")
    property bool confirmImage: false

    Connections {
        target: backend
        function onChanged(what) { if (what === "games") root.g = backend.gamesInfo() }
    }
    Timer { interval: 5000; repeat: true; running: root.g.switch.state === "running" || app.running("image")
            onTriggered: root.g = backend.gamesInfo() }

    Card {
        title: "Игровой набор"
        subtitle: "Steam, Heroic (Epic и GOG), PortProton и ProtonUp-Qt — и MangoHud для счётчика FPS"
        badge: root.kitDone ? "установлен" : ""
        Repeater {
            model: root.g.kit
            SettingRow {
                required property var modelData
                title: modelData.name
                subtitle: modelData.hint
                Text { text: modelData.installed ? "✓ есть" : "—"; color: modelData.installed ? Theme.ok : Theme.faint
                       font.pixelSize: 13 }
            }
        }
        DotProgress { visible: root.kitJob.state === "running"; value: root.kitJob.pct; text: root.kitJob.text }
        Btn { visible: !root.kitDone; text: "Установить всё"; primary: true; busy: root.kitJob.state === "running"
              onClicked: backend.installKit() }
    }

    Card {
        title: "Во время игры"
        SettingRow {
            title: "Игровой режим"
            subtitle: "Профиль питания «Мощно»" + (root.g.gamemode ? "; GameMode ускоряет игры, которые его просят" : "")
            Toggle { checked: root.g.gameMode; onToggled: function (v) { backend.setGameMode(v) } }
        }
        SettingRow {
            title: "Счётчик FPS (MangoHud) в играх Steam"
            subtitle: root.g.steam ? "FPS, загрузка процессора и видеокарты поверх игры" : "Сначала установите игровой набор"
            Toggle { enabled: root.g.steam; checked: root.g.mangohud; onToggled: function (v) { backend.setMangoHud(v) } }
        }
    }

    Card {
        title: "Видеокарта"
        subtitle: root.g.gpus.map(function (x) { return x.name }).join(" · ") || "—"
        badge: root.g.variant === "nvidia" ? "драйверы NVIDIA" : ""

        Text {
            visible: !root.g.nvidia
            text: "Для видеокарт AMD и Intel драйверы уже встроены — ничего делать не нужно."
            color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }

        ColumnLayout {
            visible: root.g.nvidia && root.g.variant !== "nvidia"
            Layout.fillWidth: true
            spacing: 10
            Text {
                text: "Для игр на NVIDIA нужна версия AstraMars с фирменным драйвером. Переход — это скачивание новой версии " +
                      "системы (10–30 минут), файлы и программы остаются. Вернуться можно в любой момент."
                color: Theme.fg; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
            DotProgress { visible: root.g.switch.state === "running"; text: "Скачиваю версию с драйверами NVIDIA…" }
            Text { visible: root.g.switch.staged === "nvidia"; text: "Готово — перезагрузите компьютер."
                   color: Theme.ok; font.pixelSize: 13 }
            Text { visible: root.g.switch.state === "failed"; text: "Не получилось скачать. Проверьте интернет и попробуйте снова."
                   color: Theme.bad; font.pixelSize: 13 }
            RowLayout {
                spacing: 10
                Btn {
                    visible: root.g.switch.staged !== "nvidia" && root.g.switch.state !== "running"
                    text: root.confirmImage ? "Да, перейти" : "Перейти на версию с NVIDIA"
                    primary: true
                    busy: app.running("image")
                    onClicked: { if (root.confirmImage) { backend.switchImage("nvidia"); root.confirmImage = false } else root.confirmImage = true }
                }
                Btn { visible: root.g.switch.staged === "nvidia"; text: "Перезагрузить"; primary: true; onClicked: backend.reboot() }
            }
        }

        ColumnLayout {
            visible: root.g.variant === "nvidia"
            Layout.fillWidth: true
            spacing: 10
            Text {
                visible: root.g.secureBoot
                text: "Включена безопасная загрузка (Secure Boot). Чтобы драйвер NVIDIA загрузился, добавьте наш ключ: нажмите кнопку, " +
                      "перезагрузитесь, на синем экране выберите Enroll MOK → Continue → Yes, введите пароль universalblue."
                color: Theme.fg; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
            RowLayout {
                spacing: 10
                Btn { visible: root.g.secureBoot; text: "Добавить ключ драйвера"; primary: true; busy: app.running("mok")
                      onClicked: backend.mokEnroll() }
                Btn { text: "Вернуть основную версию"; busy: app.running("image"); onClicked: backend.switchImage("standard") }
            }
        }
    }

    Card {
        title: "Программы и игры для Windows"
        subtitle: "Не из Steam? Попробуйте PortProton или Heroic. А .exe открываются двойным щелчком через Bottles."
        Btn { text: "Игры в Магазине"; onClicked: backend.storeSearch("игры") }
    }
}
