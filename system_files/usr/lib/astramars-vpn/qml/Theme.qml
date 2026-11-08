pragma Singleton
import QtQuick

// Палитра Ygolek VPN — как на сайте ygolek-vpn.online: ночной синий и яркий синий акцент.
// Уголёк «разгорается» холодным синим светом.
QtObject {
    readonly property color bg: "#080d17"
    readonly property color surface: "#0e1524"
    readonly property color surfaceHover: "#111a2c"
    readonly property color surface2: "#131c2f"
    readonly property color line: "#1f2a3f"
    readonly property color fg: "#e7ecf5"
    readonly property color muted: "#8b97ad"
    readonly property color faint: "#56637b"
    readonly property color accent: "#2f7bff"
    readonly property color accentLight: "#5b9bff"
    readonly property color inkOnAccent: "#ffffff"
    readonly property color glow: "#7cc4ff"
    readonly property color coal: "#121826"
    readonly property color ok: "#3fd28b"
    readonly property color warn: "#ffc857"
    readonly property color danger: "#f05252"

    readonly property string mono: "JetBrains Mono"
}
