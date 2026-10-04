import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Görünüm ve Tema yönetimi.
ColumnLayout {
    Layout.fillWidth: true
    spacing: 16

    Text {
        text: Strings.settingsAppearanceTitle
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        font.weight: Font.Bold
        font.letterSpacing: 0.5
    }

    Text {
        text: Strings.settingsThemeDesc
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
    }

    // Tema Kartları (Koyu vs Açık)
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceMd

        // Koyu Tema Kartı
        Rectangle {
            Layout.preferredWidth: 320
            Layout.preferredHeight: 140
            radius: Theme.radiusMd
            color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                   ? Qt.rgba(0.16, 0.38, 1.0, 0.12)
                   : Theme.bgSecondary
            border.color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                          ? Theme.primary
                          : Theme.borderSubtle
            border.width: (typeof settingsController !== "undefined" && settingsController.isDarkTheme) ? 2 : 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Rectangle {
                        width: 36
                        height: 36
                        radius: 18
                        color: Theme.bgPrimary

                        ModernIcon {
                            anchors.centerIn: parent
                            iconSource: Icons.moon
                            size: 18
                            color: Theme.primary
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.settingsDarkTheme
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.Bold
                        }
                        Text {
                            text: Strings.settingsDarkThemeDesc
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    radius: Theme.radiusSm
                    color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                           ? Theme.primary
                           : Theme.bgCardHover

                    Text {
                        anchors.centerIn: parent
                        text: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                              ? Strings.settingsActiveTheme
                              : Strings.settingsSwitchToDark
                        color: (typeof settingsController !== "undefined" && settingsController.isDarkTheme)
                               ? "#FFFFFF"
                               : Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof settingsController !== "undefined" && !settingsController.isDarkTheme) {
                                settingsController.toggleTheme()
                                Theme.isDark = settingsController.isDarkTheme
                            }
                        }
                    }
                }
            }
        }

        // Açık Tema Kartı
        Rectangle {
            Layout.preferredWidth: 320
            Layout.preferredHeight: 140
            radius: Theme.radiusMd
            color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                   ? Qt.rgba(0.16, 0.38, 1.0, 0.12)
                   : Theme.bgSecondary
            border.color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                          ? Theme.primary
                          : Theme.borderSubtle
            border.width: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme) ? 2 : 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Rectangle {
                        width: 36
                        height: 36
                        radius: 18
                        color: Theme.bgPrimary
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ModernIcon {
                            anchors.centerIn: parent
                            iconSource: Icons.sun
                            size: 18
                            color: Theme.warningYellow
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.settingsLightTheme
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.Bold
                        }
                        Text {
                            text: Strings.settingsLightThemeDesc
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    radius: Theme.radiusSm
                    color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                           ? Theme.primary
                           : Theme.bgCardHover

                    Text {
                        anchors.centerIn: parent
                        text: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                              ? Strings.settingsActiveTheme
                              : Strings.settingsSwitchToLight
                        color: (typeof settingsController !== "undefined" && !settingsController.isDarkTheme)
                               ? "#FFFFFF"
                               : Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof settingsController !== "undefined" && settingsController.isDarkTheme) {
                                settingsController.toggleTheme()
                                Theme.isDark = settingsController.isDarkTheme
                            }
                        }
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }
    }
}
