/*
    SPDX-FileCopyrightText: 2016 David Edmundson <davidedmundson@kde.org>
    SPDX-FileCopyrightText: 2025 Thomas Duckworth <tduck@filotimoproject.org>
    SPDX-FileCopyrightText: 2026 AstraMars OS

    SPDX-License-Identifier: LGPL-2.0-or-later

    AstraMars: часы экрана входа и блокировки.
    Как на iPhone — дата сверху, под ней крупное время; цифры точечные (шрифт Doto),
    с маленькой красной точкой-акцентом. Остальное — как в Breeze 6.8.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.plasma.clock as PlasmaClock
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: root

    readonly property bool softwareRendering: GraphicsInfo.api === GraphicsInfo.Software
    readonly property string dotFont: "Doto"
    readonly property color accent: "#ff3b30"

    spacing: 0

    // Дата: «СУББОТА, 8 НОЯБРЯ» — мелко, разрядкой, с красной точкой
    RowLayout {
        Layout.alignment: Qt.AlignHCenter
        spacing: Math.round(Kirigami.Theme.defaultFont.pointSize * 0.8)

        Rectangle {
            Layout.alignment: Qt.AlignVCenter
            implicitWidth: Math.round(Kirigami.Theme.defaultFont.pointSize * 0.7)
            implicitHeight: implicitWidth
            radius: implicitWidth / 2
            color: root.accent
        }

        PlasmaComponents3.Label {
            text: Qt.locale().toString(timeSource.dateTime, "dddd, d MMMM").toUpperCase()
            textFormat: Text.PlainText
            style: root.softwareRendering ? Text.Outline : Text.Normal
            styleColor: root.softwareRendering ? Kirigami.Theme.backgroundColor : "transparent"
            font.pointSize: Math.round(Kirigami.Theme.defaultFont.pointSize * 1.45)
            font.weight: Font.DemiBold
            font.letterSpacing: Kirigami.Theme.defaultFont.pointSize * 0.35
            opacity: 0.85
            renderType: Text.NativeRendering
        }
    }

    // Время: точечные цифры, между часами и минутами — две круглые точки, мерцают раз в секунду
    readonly property string timeText: Qt.formatTime(timeSource.dateTime, Qt.locale(), Locale.ShortFormat)
    readonly property int colonAt: timeText.indexOf(":")

    component DotDigits: PlasmaComponents3.Label {
        textFormat: Text.PlainText
        style: root.softwareRendering ? Text.Outline : Text.Normal
        styleColor: root.softwareRendering ? Kirigami.Theme.backgroundColor : "transparent"
        font.family: root.dotFont
        font.pointSize: Math.round(Kirigami.Theme.defaultFont.pointSize * 10)
        font.weight: Font.DemiBold
        // Круглые отдельные точки, как на матричных экранах: ось скругления ROND на максимум
        font.variableAxes: ({ "ROND": 100, "wght": 600 })
        font.features: { "tnum": 1 }
        renderType: Text.QtRendering
    }

    RowLayout {
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: -Math.round(Kirigami.Theme.defaultFont.pointSize * 0.6)
        spacing: Math.round(hours.font.pixelSize > 0 ? hours.font.pixelSize * 0.08 : hours.height * 0.06)

        DotDigits {
            id: hours
            text: root.colonAt > 0 ? root.timeText.slice(0, root.colonAt) : root.timeText
        }
        Column {
            id: colon
            visible: root.colonAt > 0
            Layout.alignment: Qt.AlignVCenter
            readonly property real dot: Math.max(3, Math.round(hours.height * 0.058))
            spacing: dot * 3.2
            Repeater {
                model: 2
                delegate: Rectangle {
                    width: colon.dot; height: colon.dot; radius: colon.dot / 2
                    color: Kirigami.Theme.textColor
                }
            }
            SequentialAnimation on opacity {
                running: !root.softwareRendering
                loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 500; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1; duration: 500; easing.type: Easing.InOutSine }
            }
        }
        DotDigits {
            visible: root.colonAt > 0
            text: root.colonAt > 0 ? root.timeText.slice(root.colonAt + 1) : ""
        }
    }

    PlasmaClock.Clock {
        id: timeSource
        trackSeconds: Qt.locale().timeFormat(Locale.ShortFormat).includes("s")
    }
}
