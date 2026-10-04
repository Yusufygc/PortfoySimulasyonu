import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Yapay zeka sayfası sağ panel: portföy sağlık skoru, XAI risk faktörleri ve API anahtarı durumu.
Rectangle {
    id: root
    property bool stacked: false
    Layout.fillWidth: root.stacked
    Layout.preferredWidth: root.stacked ? -1 : 340
    Layout.preferredHeight: root.stacked ? 460 : -1
    Layout.fillHeight: !root.stacked
    radius: Theme.radiusMd
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    ScrollView {
        id: rightScroll
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: ModernScrollBar {}

        ColumnLayout {
            id: colHealth
            width: rightScroll.availableWidth
            spacing: 14

            // Başlık
            Text {
                text: Strings.aiHealthScoreTitle
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Bold
                font.letterSpacing: 0.5
            }

            // Büyük Sağlık Skoru Kartı
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 110
                radius: Theme.radiusMd
                color: Theme.bgSurface
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14

                    // Büyük Dairesel Skor
                    Rectangle {
                        Layout.preferredWidth: 76
                        Layout.preferredHeight: 76
                        radius: 38
                        color: "transparent"
                        border.color: {
                            var score = (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : 75
                            if (score >= 80) return Theme.bullGreen
                            if (score >= 65) return Theme.primary
                            if (score >= 50) return Theme.accentWarning
                            return Theme.bearRed
                        }
                        border.width: 3

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: -2

                            Text {
                                text: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : "75"
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: 26
                                font.weight: Font.Bold
                                Layout.alignment: Qt.AlignHCenter
                            }

                            Text {
                                text: "/ 100"
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: 9
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }
                    }

                    // Skor Etiketi & Bilgisi
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Rectangle {
                            Layout.preferredHeight: 22
                            Layout.preferredWidth: lblBadge.implicitWidth + 16
                            radius: 11
                            color: {
                                var score = (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : 75
                                if (score >= 80) return Qt.rgba(0.06, 0.72, 0.51, 0.15)
                                if (score >= 65) return Qt.rgba(0.38, 0.40, 0.95, 0.15)
                                if (score >= 50) return Qt.rgba(0.96, 0.62, 0.18, 0.15)
                                return Qt.rgba(0.94, 0.27, 0.24, 0.15)
                            }

                            Text {
                                id: lblBadge
                                anchors.centerIn: parent
                                text: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.healthScoreLabel : "Dengeli"
                                color: {
                                    var score = (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.portfolioHealthScore : 75
                                    if (score >= 80) return Theme.bullGreen
                                    if (score >= 65) return Theme.primary
                                    if (score >= 50) return Theme.accentWarning
                                    return Theme.bearRed
                                }
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: Strings.aiHealthScoreDesc
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            // Ayırıcı
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderSubtle
            }

            // XAI Risk Faktörleri Başlığı
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: Strings.aiXaiInsightsTitle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.Bold
                    font.letterSpacing: 0.5
                    Layout.fillWidth: true
                }

                ModernIcon {
                    iconSource: Icons.activity
                    size: 14
                    color: Theme.textMuted
                }
            }

            // 4 Risk & Sağlık Boyutu Listesi
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10

                Repeater {
                    model: (typeof aiAdvisorController !== "undefined") ? aiAdvisorController.healthFactors : []

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        radius: Theme.radiusSm
                        color: Theme.bgSurface
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 6

                            RowLayout {
                                Layout.fillWidth: true

                                Text {
                                    text: modelData.title
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.DemiBold
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: modelData.value
                                    color: modelData.isGood ? Theme.bullGreen : Theme.accentWarning
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Bold
                                }
                            }

                            // İlerleme Çubuğu
                            Rectangle {
                                Layout.fillWidth: true
                                height: 4
                                radius: 2
                                color: Theme.bgCard

                                Rectangle {
                                    height: parent.height
                                    width: parent.width * Math.min(1.0, (modelData.score / (modelData.maxScore || 25)))
                                    radius: 2
                                    color: modelData.isGood ? Theme.bullGreen : Theme.accentWarning
                                }
                            }

                            Text {
                                text: modelData.status
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            // Ayırıcı
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderSubtle
            }

            // API Anahtarı Durumu / Tanımlama Kartı
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey) ? 44 : 110
                radius: Theme.radiusSm
                color: Theme.bgSurface
                border.color: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)
                ? Qt.rgba(0.06, 0.72, 0.51, 0.3)
                : Qt.rgba(0.96, 0.62, 0.18, 0.3)
                border.width: 1

                // Durum 1: API Key Mevcut
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    visible: (typeof aiAdvisorController !== "undefined" && aiAdvisorController.hasApiKey)

                    ModernIcon {
                        iconSource: Icons.check
                        size: 16
                        color: Theme.bullGreen
                    }

                    Text {
                        text: Strings.aiGeminiActive
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Medium
                        Layout.fillWidth: true
                    }
                }

                // Durum 2: API Key Tanımlanmamış
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    visible: (typeof aiAdvisorController !== "undefined" && !aiAdvisorController.hasApiKey)

                    Text {
                        Layout.fillWidth: true
                        text: Strings.aiApiKeyMissingNotice
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 30
                            radius: 4
                            color: Theme.bgCard
                            border.color: Theme.borderSubtle
                            border.width: 1

                            TextInput {
                                id: txtApiKey
                                anchors.fill: parent
                                anchors.margins: 6
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                clip: true
                                echoMode: TextInput.Password

                                Text {
                                    text: Strings.aiKeyPlaceholder
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    visible: !txtApiKey.text
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }

                        Rectangle {
                            Layout.preferredWidth: 64
                            Layout.preferredHeight: 30
                            radius: 4
                            color: Theme.primary

                            Text {
                                anchors.centerIn: parent
                                text: Strings.btnSave
                                color: "#FFFFFF"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.DemiBold
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (txtApiKey.text.trim().length > 5 && typeof aiAdvisorController !== "undefined") {
                                        aiAdvisorController.saveApiKey(txtApiKey.text)
                                        txtApiKey.text = ""
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Metrikleri Yenile Butonu
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                radius: Theme.radiusSm
                color: btnRefreshMouse.containsMouse ? Theme.bgSurfaceHover : Theme.bgSurface
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6

                    ModernIcon {
                        iconSource: Icons.refresh
                        size: 14
                        color: Theme.textSecondary
                    }

                    Text {
                        text: Strings.aiRefreshHealthMetrics
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Medium
                    }
                }

                MouseArea {
                    id: btnRefreshMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof aiAdvisorController !== "undefined") {
                            aiAdvisorController.refreshHealthScore()
                        }
                    }
                }
            }
        }
    }
}
