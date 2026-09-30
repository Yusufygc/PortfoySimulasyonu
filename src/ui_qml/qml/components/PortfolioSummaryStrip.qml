import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

RowLayout {
    id: root

    spacing: Theme.spaceMd

    // 1. Net Sermaye
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 84
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceMd
            spacing: Theme.spaceSm

            Rectangle {
                width: 38
                height: 38
                radius: Theme.radiusSm
                color: Theme.accentSoft

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.get("capital")
                    iconColor: Theme.accent
                    width: 18
                    height: 18
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: Strings.portfolioKpiNetCapital
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Text {
                    text: portfolioController.summaryNetCapital
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
            }
        }
    }

    // 2. Nakit Bakiye
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 84
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceMd
            spacing: Theme.spaceSm

            Rectangle {
                width: 38
                height: 38
                radius: Theme.radiusSm
                color: Theme.bgSecondary

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.get("coins")
                    iconColor: Theme.textSecondary
                    width: 18
                    height: 18
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: Strings.portfolioKpiCash
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Text {
                    text: portfolioController.summaryRemainingCash
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
            }
        }
    }

    // 3. Toplam Değer
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 84
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceMd
            spacing: Theme.spaceSm

            Rectangle {
                width: 38
                height: 38
                radius: Theme.radiusSm
                color: Theme.bgSecondary

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.get("barchart")
                    iconColor: Theme.textSecondary
                    width: 18
                    height: 18
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: Strings.portfolioKpiTotalValue
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                Text {
                    text: portfolioController.summaryTotalValue
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
            }
        }
    }

    // 4. Kâr / Zarar
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 84
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderCard
        border.width: 1

        // Sol renkli vurgu şeridi
        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 4
            radius: 2
            color: {
                if (portfolioController.summaryProfitLossState === "positive") return Theme.bullGreen
                if (portfolioController.summaryProfitLossState === "negative") return Theme.bearRed
                return Theme.borderSubtle
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spaceMd + 4
            anchors.rightMargin: Theme.spaceMd
            anchors.topMargin: Theme.spaceMd
            anchors.bottomMargin: Theme.spaceMd
            spacing: Theme.spaceSm

            Rectangle {
                width: 38
                height: 38
                radius: Theme.radiusSm
                color: {
                    if (portfolioController.summaryProfitLossState === "positive") return Theme.bullGreenSoft
                    if (portfolioController.summaryProfitLossState === "negative") return Theme.bearRedSoft
                    return Theme.bgSecondary
                }

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.get(portfolioController.summaryProfitLossState === "negative" ? "trendingdown" : "trendingup")
                    iconColor: {
                        if (portfolioController.summaryProfitLossState === "positive") return Theme.bullGreen
                        if (portfolioController.summaryProfitLossState === "negative") return Theme.bearRed
                        return Theme.textMuted
                    }
                    width: 18
                    height: 18
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs

                    Text {
                        text: Strings.portfolioKpiProfitLoss
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                    }

                    Item { Layout.fillWidth: true }

                    // Yüzde Rozeti
                    Rectangle {
                        height: 18
                        width: pctText.width + 10
                        radius: Theme.radiusFull
                        color: {
                            if (portfolioController.summaryProfitLossState === "positive") return Theme.bullGreenSoft
                            if (portfolioController.summaryProfitLossState === "negative") return Theme.bearRedSoft
                            return Theme.borderSubtle
                        }

                        Text {
                            id: pctText
                            anchors.centerIn: parent
                            text: (portfolioController.summaryProfitLossPct >= 0 ? "+" : "") +
                                  portfolioController.summaryProfitLossPct.toFixed(2) + "%"
                            color: {
                                if (portfolioController.summaryProfitLossState === "positive") return Theme.bullGreen
                                if (portfolioController.summaryProfitLossState === "negative") return Theme.bearRed
                                return Theme.textMuted
                            }
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                        }
                    }
                }

                Text {
                    text: portfolioController.summaryProfitLoss
                    color: {
                        if (portfolioController.summaryProfitLossState === "positive") return Theme.bullGreen
                        if (portfolioController.summaryProfitLossState === "negative") return Theme.bearRed
                        return Theme.textPrimary
                    }
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
            }
        }
    }
}
