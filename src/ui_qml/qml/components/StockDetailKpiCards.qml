import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse detayı pozisyon KPI kartları: toplam lot, ortalama maliyet, piyasa değeri, net kâr/zarar.
GridLayout {
    id: root
    property real boxWidth: 0
    Layout.fillWidth: true
    columns: root.boxWidth < 700 ? 2 : 4
    columnSpacing: Theme.spaceMd
    rowSpacing: Theme.spaceMd
    uniformCellWidths: true

    // 1. Toplam Lot
    Rectangle {
        Layout.fillWidth: true
        height: 72
        radius: Theme.radiusSm
        color: Theme.bgCard
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 2

            Text {
                text: Strings.stockDetailKpiQty
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }
            Text {
                text: (typeof stockDetailController !== "undefined") ? stockDetailController.quantityStr : "0 Lot"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontLg
                font.weight: Font.Bold
            }
        }
    }

    // 2. Ortalama Maliyet
    Rectangle {
        Layout.fillWidth: true
        height: 72
        radius: Theme.radiusSm
        color: Theme.bgCard
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 2

            Text {
                text: Strings.stockDetailKpiCost
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }
            Text {
                text: (typeof stockDetailController !== "undefined") ? stockDetailController.avgCostStr : "₺0.00"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontLg
                font.weight: Font.Bold
            }
        }
    }

    // 3. Piyasa Değeri
    Rectangle {
        Layout.fillWidth: true
        height: 72
        radius: Theme.radiusSm
        color: Theme.bgCard
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 2

            Text {
                text: Strings.stockDetailKpiValue
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }
            Text {
                text: (typeof stockDetailController !== "undefined") ? stockDetailController.marketValueStr : "₺0.00"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontLg
                font.weight: Font.Bold
            }
        }
    }

    // 4. Net Kâr / Zarar
    Rectangle {
        Layout.fillWidth: true
        height: 72
        radius: Theme.radiusSm
        color: (typeof stockDetailController !== "undefined" && stockDetailController.isPnlPositive)
        ? Theme.bullGreenSoft
        : Theme.bearRedSoft
        border.color: (typeof stockDetailController !== "undefined" && stockDetailController.isPnlPositive)
        ? Theme.bullGreen
        : Theme.bearRed
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 2

            Text {
                text: Strings.stockDetailKpiPnl
                color: (typeof stockDetailController !== "undefined" && stockDetailController.isPnlPositive)
                ? Theme.bullGreen
                : Theme.bearRed
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }
            RowLayout {
                spacing: 8
                Text {
                    text: (typeof stockDetailController !== "undefined") ? stockDetailController.unrealizedPnlStr : "₺0.00"
                    color: (typeof stockDetailController !== "undefined" && stockDetailController.isPnlPositive)
                    ? Theme.bullGreen
                    : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                }
                Text {
                    text: (typeof stockDetailController !== "undefined") ? stockDetailController.unrealizedPnlPctStr : "%0.00"
                    color: (typeof stockDetailController !== "undefined" && stockDetailController.isPnlPositive)
                    ? Theme.bullGreen
                    : Theme.bearRed
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                }
            }
        }
    }
}
