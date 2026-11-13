import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Dışa Aktarım ve Yedekleme: Excel/JSON dışa aktarma.
ColumnLayout {
    Layout.fillWidth: true
    spacing: 16

    Text {
        text: Strings.settingsExportTitle
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        font.weight: Font.Bold
        font.letterSpacing: 0.5
    }

    // Excel Export Kartı
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 120
        radius: Theme.radiusMd
        color: Theme.bgSecondary
        border.color: Theme.borderSubtle
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 16

            Rectangle {
                Layout.preferredWidth: 48
                Layout.preferredHeight: 48
                radius: 24
                color: Qt.rgba(0.06, 0.72, 0.51, 0.15)

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.fileText
                    size: 24
                    color: Theme.bullGreen
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: Strings.settingsExportExcel
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.Bold
                }

                Text {
                    Layout.fillWidth: true
                    text: Strings.settingsExportExcelDesc
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    wrapMode: Text.Wrap
                }
            }

            Rectangle {
                Layout.preferredWidth: 160
                Layout.preferredHeight: 38
                radius: Theme.radiusSm
                color: btnExcelMouse.containsMouse ? Theme.bullGreenSoft : Theme.bullGreen

                Text {
                    anchors.centerIn: parent
                    text: Strings.settingsExportExcelButton
                    color: "#FFFFFF"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    id: btnExcelMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof settingsController !== "undefined") {
                            settingsController.exportPortfolioToExcel()
                        }
                    }
                }
            }
        }
    }

    // JSON Export Kartı
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 120
        radius: Theme.radiusMd
        color: Theme.bgSecondary
        border.color: Theme.borderSubtle
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 16

            Rectangle {
                Layout.preferredWidth: 48
                Layout.preferredHeight: 48
                radius: 24
                color: Qt.rgba(0.16, 0.38, 1.0, 0.15)

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.settings
                    size: 24
                    color: Theme.primary
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: Strings.settingsExportJson
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.Bold
                }

                Text {
                    Layout.fillWidth: true
                    text: Strings.settingsExportJsonDesc
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    wrapMode: Text.Wrap
                }
            }

            Rectangle {
                Layout.preferredWidth: 160
                Layout.preferredHeight: 38
                radius: Theme.radiusSm
                color: btnJsonMouse.containsMouse ? Theme.primaryHover : Theme.primary

                Text {
                    anchors.centerIn: parent
                    text: Strings.settingsExportJsonButton
                    color: "#FFFFFF"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    id: btnJsonMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof settingsController !== "undefined") {
                            settingsController.exportPortfolioToJson()
                        }
                    }
                }
            }
        }
    }
}
