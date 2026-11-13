import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > API Anahtarları ve Entegrasyonlar: Gemini/EVDS anahtarları ve bağlantı testi.
ColumnLayout {
    Layout.fillWidth: true
    spacing: 16

    Text {
        text: Strings.settingsApiTitle
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        font.weight: Font.Bold
        font.letterSpacing: 0.5
    }

    // 1. Google Gemini API Kartı
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 185
        radius: Theme.radiusMd
        color: Theme.bgSecondary
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: Strings.settingsGeminiKeyTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.Bold
                    Layout.fillWidth: true
                }
                Text {
                    text: Strings.settingsGeminiModel
                    color: Theme.primary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                }
            }

            Text {
                Layout.fillWidth: true
                text: Strings.settingsGeminiKeyDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: inputGeminiKey.activeFocus ? Theme.primary : Theme.borderSubtle
                    border.width: 1

                    TextInput {
                        id: inputGeminiKey
                        anchors.fill: parent
                        anchors.margins: 8
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        echoMode: btnToggleMask.showKey ? TextInput.Normal : TextInput.Password
                        text: (typeof settingsController !== "undefined") ? settingsController.geminiApiKey : ""
                        clip: true
                    }
                }

                // Göster/Gizle Butonu
                Rectangle {
                    id: btnToggleMask
                    property bool showKey: false
                    Layout.preferredWidth: 38
                    Layout.preferredHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgCardHover
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ModernIcon {
                        anchors.centerIn: parent
                        iconSource: btnToggleMask.showKey ? Icons.sun : Icons.moon
                        size: 14
                        color: Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: btnToggleMask.showKey = !btnToggleMask.showKey
                    }
                }

                // Bağlantıyı Test Et Butonu
                Rectangle {
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgCardHover
                    border.color: Theme.borderSubtle
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6

                        ModernIcon {
                            iconSource: Icons.zap
                            size: 14
                            color: Theme.primary
                        }

                        Text {
                            text: Strings.settingsBtnTestConnection
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.Medium
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof settingsController !== "undefined") {
                                settingsController.testGeminiApiKey(inputGeminiKey.text)
                            }
                        }
                    }
                }
            }

            // Test Sonuç Rozeti
            Text {
                visible: (typeof settingsController !== "undefined") && settingsController.apiTestResult.length > 0
                text: (typeof settingsController !== "undefined") ? settingsController.apiTestResult : ""
                color: (typeof settingsController !== "undefined" && settingsController.apiTestResult.indexOf("Başarılı") !== -1)
                       ? Theme.bullGreen
                       : Theme.bearRed
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Medium
            }
        }
    }

    // 2. TCMB EVDS API Kartı
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 145
        radius: Theme.radiusMd
        color: Theme.bgSecondary
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            Text {
                text: Strings.settingsEvdsKeyTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: Font.Bold
            }

            Text {
                Layout.fillWidth: true
                text: Strings.settingsEvdsKeyDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: inputEvdsKey.activeFocus ? Theme.primary : Theme.borderSubtle
                border.width: 1

                TextInput {
                    id: inputEvdsKey
                    anchors.fill: parent
                    anchors.margins: 8
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    echoMode: TextInput.Password
                    text: (typeof settingsController !== "undefined") ? settingsController.evdsApiKey : ""
                    clip: true
                }
            }
        }
    }

    // Kaydet Butonu
    Rectangle {
        Layout.preferredWidth: 220
        Layout.preferredHeight: 38
        radius: Theme.radiusSm
        color: btnSaveKeyMouse.containsMouse ? Theme.primaryHover : Theme.primary

        RowLayout {
            anchors.centerIn: parent
            spacing: 8

            ModernIcon {
                iconSource: Icons.check
                size: 14
                color: "#FFFFFF"
            }

            Text {
                text: Strings.settingsSaveApiKeys
                color: "#FFFFFF"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
            }
        }

        MouseArea {
            id: btnSaveKeyMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (typeof settingsController !== "undefined") {
                    settingsController.saveApiKeys(inputGeminiKey.text, inputEvdsKey.text)
                }
            }
        }
    }
}
