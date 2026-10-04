import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse 360 görünüm modu sekme çubuğu: Genel Bakış / Finansal Performans / KAP Ortaklık Yapısı.
Rectangle {
    id: root
    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    Layout.fillWidth: true
    implicitHeight: 46
    radius: Theme.radiusMd
    color: Theme.bgCard
    border.color: Theme.borderSubtle
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 6

        // Sekme 0: Genel Bakış & Özet
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusSm
            color: (root.ctrl && root.ctrl.viewMode === 0) ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15) : "transparent"
            border.color: (root.ctrl && root.ctrl.viewMode === 0) ? Theme.accent : "transparent"
            border.width: 1

            RowLayout {
                anchors.centerIn: parent
                spacing: 8

                ModernIcon {
                    name: "target"
                    size: 14
                    color: (root.ctrl && root.ctrl.viewMode === 0) ? Theme.accent : Theme.textMuted
                }

                Text {
                    text: Strings.tabOverviewAndCharts
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: (root.ctrl && root.ctrl.viewMode === 0) ? Font.Bold : Font.Normal
                    color: (root.ctrl && root.ctrl.viewMode === 0) ? Theme.accent : Theme.textSecondary
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.ctrl) root.ctrl.setViewMode(0)
                }
            }
        }

        // Sekme 1: Kapsamlı Bilanço & Finansal Tablolar
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusSm
            color: (root.ctrl && root.ctrl.viewMode === 1) ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15) : "transparent"
            border.color: (root.ctrl && root.ctrl.viewMode === 1) ? Theme.accent : "transparent"
            border.width: 1

            RowLayout {
                anchors.centerIn: parent
                spacing: 8

                ModernIcon {
                    name: "layers"
                    size: 14
                    color: (root.ctrl && root.ctrl.viewMode === 1) ? Theme.accent : Theme.textMuted
                }

                Text {
                    text: Strings.tabFullFinancials
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: (root.ctrl && root.ctrl.viewMode === 1) ? Font.Bold : Font.Normal
                    color: (root.ctrl && root.ctrl.viewMode === 1) ? Theme.accent : Theme.textSecondary
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.ctrl) root.ctrl.setViewMode(1)
                }
            }
        }

        // Sekme 2: KAP Ortaklık Tarihçesi
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radiusSm
            color: (root.ctrl && root.ctrl.viewMode === 2) ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15) : "transparent"
            border.color: (root.ctrl && root.ctrl.viewMode === 2) ? Theme.accent : "transparent"
            border.width: 1

            RowLayout {
                anchors.centerIn: parent
                spacing: 8

                ModernIcon {
                    name: "history"
                    size: 14
                    color: (root.ctrl && root.ctrl.viewMode === 2) ? Theme.accent : Theme.textMuted
                }

                Text {
                    text: Strings.tabShareholdersTimeline
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: (root.ctrl && root.ctrl.viewMode === 2) ? Font.Bold : Font.Normal
                    color: (root.ctrl && root.ctrl.viewMode === 2) ? Theme.accent : Theme.textSecondary
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.ctrl) root.ctrl.setViewMode(2)
                }
            }
        }
    }
}
