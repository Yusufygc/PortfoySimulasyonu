import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse detayı üst başlık: breadcrumb, hisse adı/fiyat, grafik/Hisse 360 kısayolları, sermaye artırımı ve temettü, kapat.
GridLayout {
    id: root
    property bool stacked: false
    signal openChartRequested(string ticker)
    signal openStock360Requested(string ticker)
    signal corporateActionRequested()
    signal dividendRequested()
    Layout.fillWidth: true
    columns: root.stacked ? 1 : 2
    columnSpacing: Theme.spaceMd
    rowSpacing: Theme.spaceSm

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4

        // Breadcrumb
        RowLayout {
            spacing: 6
            Text {
                text: Strings.stockDetailBreadcrumb
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }
            Text {
                text: ">"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
            Text {
                text: (typeof stockDetailController !== "undefined") ? stockDetailController.portfolioName : Strings.stockDetailPortfolioFallback
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
            Text {
                text: ">"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
            Text {
                text: (typeof stockDetailController !== "undefined") ? stockDetailController.ticker : ""
                color: Theme.primary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.Bold
            }
        }

        // Ticker, Şirket Adı ve Fiyat Rozeti
        RowLayout {
            spacing: Theme.spaceSm

            Text {
                text: (typeof stockDetailController !== "undefined") ? stockDetailController.ticker : ""
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXl
                font.weight: Font.Bold
            }

            Text {
                text: (typeof stockDetailController !== "undefined") ? stockDetailController.companyName : ""
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            // Canlı Fiyat Etiketi
            Rectangle {
                height: 28
                radius: Theme.radiusSm
                color: Theme.bgCard
                border.color: Theme.borderSubtle
                border.width: 1
                Layout.preferredWidth: rowPriceBadge.implicitWidth + 16

                RowLayout {
                    id: rowPriceBadge
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        text: (typeof stockDetailController !== "undefined") ? stockDetailController.currentPriceStr : "₺-"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                    }

                    Text {
                        text: (typeof stockDetailController !== "undefined") ? stockDetailController.dailyDiffStr : "%0.00"
                        color: (typeof stockDetailController !== "undefined" && stockDetailController.isDailyPositive)
                        ? Theme.bullGreen
                        : Theme.bearRed
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                    }
                }
            }
        }
    }

    // Hızlı Aksiyon Butonları
    Flow {
        Layout.alignment: root.stacked ? Qt.AlignLeft : Qt.AlignRight
        Layout.fillWidth: root.stacked
        spacing: 8

        // TradingView Grafiğinde Aç
        ModernButton {
            text: Strings.stockDetailBtnTv
            iconName: "candle"
            variant: "ghost"
            implicitHeight: 34
            onClicked: {
                if (typeof stockDetailController !== "undefined") {
                    const t = stockDetailController.ticker
                    stockDetailController.close()
                    root.openChartRequested(t)
                }
            }
        }

        // Hisse 360 Temel Analizi
        ModernButton {
            text: Strings.stockDetailBtn360
            iconName: "stock360"
            variant: "ghost"
            implicitHeight: 34
            onClicked: {
                if (typeof stockDetailController !== "undefined") {
                    const t = stockDetailController.ticker
                    stockDetailController.close()
                    root.openStock360Requested(t)
                }
            }
        }

        // Sermaye Artırımı (bedelli / bedelsiz) — yalnızca ana portföy pozisyonlarında
        ModernButton {
            visible: (typeof stockDetailController !== "undefined")
            && !stockDetailController.isModelContext
            && stockDetailController.quantity > 0
            text: Strings.caBtnOpen
            iconName: "layers"
            variant: "ghost"
            implicitHeight: 34
            onClicked: root.corporateActionRequested()
        }

        // Nakit temettü kaydı — yalnızca ana portföy pozisyonlarında
        ModernButton {
            visible: (typeof stockDetailController !== "undefined")
            && !stockDetailController.isModelContext
            && stockDetailController.quantity > 0
            text: Strings.dividendBtnOpen
            iconName: "coins"
            variant: "ghost"
            implicitHeight: 34
            onClicked: root.dividendRequested()
        }

        // Excel'e Aktar
        ModernButton {
            text: Strings.stockDetailBtnExcel
            iconName: "filetext"
            variant: "secondary"
            implicitHeight: 34
            onClicked: {
                if (typeof stockDetailController !== "undefined") {
                    stockDetailController.exportStockToExcel()
                }
            }
        }

        // Kapat Butonu
        Rectangle {
            width: 34
            height: 34
            radius: Theme.radiusSm
            color: btnCloseMouse.containsMouse ? Theme.bgCardHover : Theme.bgCard
            border.color: Theme.borderSubtle
            border.width: 1

            ModernIcon {
                anchors.centerIn: parent
                iconSource: Icons.close
                size: 14
                color: Theme.textSecondary
            }

            MouseArea {
                id: btnCloseMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (typeof stockDetailController !== "undefined") {
                        stockDetailController.close()
                    }
                }
            }
        }
    }
}
