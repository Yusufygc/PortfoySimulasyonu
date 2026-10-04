import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Optimizasyon KPI şeridi: Maksimum Sharpe, getiri, risk ve ağırlık sayısı kartları (dar alanda 2x2).
GridLayout {
    id: root
    property bool stacked: false
    property real hostWidth: 0
    Layout.fillWidth: true
    columns: (root.stacked ? root.hostWidth < 800 : root.hostWidth < 1280) ? 2 : 4
    columnSpacing: Theme.spaceMd
    rowSpacing: Theme.spaceMd
    uniformCellWidths: true

    // Kart 1: Maksimum Sharpe
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 88
        radius: Theme.radiusMd
        color: Theme.bgCard
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: Theme.spaceSm

            Rectangle {
                width: 36
                height: 36
                radius: Theme.radiusSm
                color: Theme.accentSoft

                ModernIcon {
                    anchors.centerIn: parent
                    name: "target"
                    color: Theme.accent
                    size: 18
                }
            }

            ColumnLayout {
                spacing: 2
                Text {
                    text: Strings.optKpiSharpe
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }
                Text {
                    text: optimizationController.optimalSharpeFormatted
                    color: optimizationController.isOptimalSharpePositive ? Theme.textPrimary : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
                Text {
                    text: Strings.optCurrentPrefix + optimizationController.currentSharpeFormatted
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                }
            }
        }
    }

    // Kart 2: Beklenen Getiri
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 88
        radius: Theme.radiusMd
        color: Theme.bgCard
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: Theme.spaceSm

            Rectangle {
                width: 36
                height: 36
                radius: Theme.radiusSm
                color: optimizationController.isOptimalReturnPositive ? Theme.bullGreenSoft : Theme.bearRedSoft

                ModernIcon {
                    anchors.centerIn: parent
                    name: optimizationController.isOptimalReturnPositive ? "trendingup" : "trendingdown"
                    color: optimizationController.isOptimalReturnPositive ? Theme.bullGreen : Theme.bearRed
                    size: 18
                }
            }

            ColumnLayout {
                spacing: 2
                Text {
                    text: Strings.optKpiExpReturn
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }
                Text {
                    text: optimizationController.optimalReturnFormatted
                    color: optimizationController.isOptimalReturnPositive ? Theme.bullGreen : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
                Text {
                    text: Strings.optCurrentPrefix + optimizationController.currentReturnFormatted
                    color: optimizationController.isCurrentReturnPositive ? Theme.textSecondary : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                }
            }
        }
    }

    // Kart 3: Yıllık Volatilite (Risk)
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 88
        radius: Theme.radiusMd
        color: Theme.bgCard
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: Theme.spaceSm

            Rectangle {
                width: 36
                height: 36
                radius: Theme.radiusSm
                color: Theme.warningYellowSoft

                ModernIcon {
                    anchors.centerIn: parent
                    name: "shieldcheck"
                    color: Theme.warningYellow
                    size: 18
                }
            }

            ColumnLayout {
                spacing: 2
                Text {
                    text: Strings.optKpiVolatility
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }
                Text {
                    text: optimizationController.optimalVolFormatted
                    color: Theme.warningYellow
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
                Text {
                    text: Strings.optCurrentPrefix + optimizationController.currentVolFormatted
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                }
            }
        }
    }

    // Kart 4: Minimum Risk Portföyü
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 88
        radius: Theme.radiusMd
        color: Theme.bgCard
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: Theme.spaceSm

            Rectangle {
                width: 36
                height: 36
                radius: Theme.radiusSm
                color: Theme.accentSoft

                ModernIcon {
                    anchors.centerIn: parent
                    name: "piechart"
                    color: Theme.accent
                    size: 18
                }
            }

            ColumnLayout {
                spacing: 2
                Text {
                    text: Strings.optKpiMinVol
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }
                Text {
                    text: optimizationController.minVolFormatted
                    color: Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
                Text {
                    text: Strings.optMinRiskLabel
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                }
            }
        }
    }
}
