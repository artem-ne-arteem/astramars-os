pragma Singleton
import QtQuick

// Палитра AstraMars: чёрный, белый и один акцент. Акцент выбирается в Оформлении
// и приходит из main.py (astraAccent) — одинаковый во всех наших приложениях.
QtObject {
    readonly property color bg: "#000000"
    readonly property color side: "#070707"
    readonly property color surface: "#0e0e0e"
    readonly property color surfaceHover: "#151515"
    readonly property color surface2: "#1b1b1b"
    readonly property color line: "#262626"
    readonly property color fg: "#f2f2f2"
    readonly property color muted: "#8c8c8c"
    readonly property color faint: "#555555"
    readonly property color ok: "#30d158"
    readonly property color warn: "#ff9f0a"
    readonly property color bad: "#ff453a"
    readonly property color accent: typeof astraAccent !== "undefined" && astraAccent ? astraAccent : "#ff3b30"
    readonly property color glass: Qt.rgba(1, 1, 1, 0.06)
    function soft(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }

    readonly property string dots: "Doto"
    readonly property string mono: "JetBrains Mono"
}
