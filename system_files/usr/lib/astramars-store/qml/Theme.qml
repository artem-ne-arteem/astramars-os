pragma Singleton
import QtQuick

// Палитра AstraMars: чёрный, белый и один красный акцент (как на экране входа)
QtObject {
    readonly property color bg: "#000000"
    readonly property color surface: "#0e0e0e"
    readonly property color surfaceHover: "#151515"
    readonly property color surface2: "#1b1b1b"
    readonly property color line: "#272727"
    readonly property color fg: "#f2f2f2"
    readonly property color muted: "#8c8c8c"
    readonly property color faint: "#555555"
    readonly property color accent: typeof astraAccent !== "undefined" && astraAccent ? astraAccent : "#ff3b30"
    readonly property color glass: Qt.rgba(1, 1, 1, 0.06)

    readonly property string dots: "Doto"
}
