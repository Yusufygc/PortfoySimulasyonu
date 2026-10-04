import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Yapay zeka sayfası üst başlık: başlık, model/durum rozeti, sohbet geçmişi ve temizle eylemleri.
RowLayout {
    id: root
    signal historyRequested()
    Layout.fillWidth: true
    spacing: Theme.spaceMd

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2

        Text {
            text: Strings.aiAdvisorTitle
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXl
            font.weight: Font.Bold
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Text {
            text: Strings.aiAdvisorSubtitle
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }

    // Model ve Durum Rozeti
    Rectangle {
        Layout.preferredHeight: 36
        Layout.preferredWidth: rowStatus.implicitWidth + 24
        radius: Theme.radiusMd
        color: Theme.bgSurface
        border.color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
        ? Theme.primary
        : Theme.borderSubtle
        border.width: 1

        RowLayout {
            id: rowStatus
            anchors.centerIn: parent
            spacing: Theme.spaceXs

            // Durum Işığı
            Rectangle {
                width: 8
                height: 8
                radius: 4
                color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.isLoading)
                ? Theme.accentWarning
                : (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                ? Theme.bullGreen
                : Theme.primary

                SequentialAnimation on opacity {
                    running: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.isLoading)
                    loops: Animation.Infinite
                    PropertyAnimation { to: 0.3; duration: 600 }
                    PropertyAnimation { to: 1.0; duration: 600 }
                }
            }

            Text {
                text: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.modelName : "Gemini 2.5 Flash"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }

            Text {
                text: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                ? Strings.aiBadgeOnline
                : Strings.aiBadgeSimulation
                color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                ? Theme.bullGreen
                : Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
        }
    }

    // Sohbet Geçmişi Butonu
    Rectangle {
        visible: typeof aiAdvisorController !== "undefined" && aiAdvisorController.historyAvailable
        Layout.preferredHeight: 36
        Layout.preferredWidth: rowHistory.implicitWidth + 20
        radius: Theme.radiusMd
        color: btnHistoryMouse.containsMouse ? Theme.bgSurfaceHover : Theme.bgSurface
        border.color: Theme.borderSubtle
        border.width: 1

        RowLayout {
            id: rowHistory
            anchors.centerIn: parent
            spacing: Theme.spaceXs

            ModernIcon {
                iconSource: Icons.history
                size: 14
                color: Theme.textSecondary
            }

            Text {
                text: Strings.aiHistory
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Medium
            }
        }

        MouseArea {
            id: btnHistoryMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.historyRequested()
        }
    }

    // Yeni Sohbet Butonu (eski ad: Sohbeti Temizle; geçmiş korunur)
    Rectangle {
        Layout.preferredHeight: 36
        Layout.preferredWidth: rowClear.implicitWidth + 20
        radius: Theme.radiusMd
        color: btnClearMouse.containsMouse ? Theme.bgSurfaceHover : Theme.bgSurface
        border.color: Theme.borderSubtle
        border.width: 1

        RowLayout {
            id: rowClear
            anchors.centerIn: parent
            spacing: Theme.spaceXs

            ModernIcon {
                iconSource: Icons.trash
                size: 14
                color: Theme.textSecondary
            }

            Text {
                text: Strings.aiClearChat
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Medium
            }
        }

        MouseArea {
            id: btnClearMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (typeof aiAdvisorController !== "undefined") {
                    aiAdvisorController.clearChat()
                }
            }
        }
    }
}
