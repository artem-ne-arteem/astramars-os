import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

// Виджет рабочего стола: само оформление — в DotClock.qml (чистый QtQuick, проверяется при сборке)
PlasmoidItem {
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    preferredRepresentation: fullRepresentation
    fullRepresentation: DotClock {
        Layout.minimumWidth: 220
        Layout.minimumHeight: 120
        Layout.preferredWidth: 420
        Layout.preferredHeight: 200
    }
}
