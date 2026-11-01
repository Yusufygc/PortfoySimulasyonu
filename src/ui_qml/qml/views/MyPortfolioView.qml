import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    ScrollView {
        id: mainScrollView
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ScrollBar.vertical: ModernScrollBar {
            parent: mainScrollView
            x: mainScrollView.mirrored ? 2 : mainScrollView.width - width - 3
            y: mainScrollView.topPadding + 2
            height: mainScrollView.availableHeight - 4
            active: mainScrollView.ScrollBar.vertical.active
        }

        ColumnLayout {
            width: mainScrollView.availableWidth
            spacing: Theme.spaceMd

            // Üst Başlık ve Aksiyon Butonları (dar pencerede butonlar başlığın altına geçer)
            GridLayout {
                Layout.fillWidth: true
                columns: root.width < 1060 ? 1 : 2
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceSm

                Column {
                    spacing: 2
                    Text {
                        text: Strings.myPortfolioTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                    Text {
                        text: Strings.myPortfolioSubtitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                    PriceStatusChip {}
                }

                Flow {
                    Layout.alignment: root.width < 1060 ? Qt.AlignLeft : Qt.AlignRight
                    Layout.fillWidth: root.width < 1060
                    spacing: Theme.spaceSm

                    // Sermaye Yönetimi Butonu
                    ModernButton {
                        text: Strings.btnCapital
                        iconName: "capital"
                        variant: "secondary"
                        onClicked: capitalModal.open()
                    }

                    // Excel Raporu Butonu
                    ModernButton {
                        text: Strings.btnExportExcel
                        iconName: "filetext"
                        variant: "secondary"
                        onClicked: {
                            if (typeof dashboardController !== "undefined") {
                                excelDialog.open(dashboardController.firstTradeDateText(), "Portfoy_Raporu.xlsx")
                            }
                        }
                    }

                    // Hızlı Al/Sat Butonu
                    ModernButton {
                        text: Strings.btnQuickTrade
                        iconName: "zap"
                        variant: "primary"
                        onClicked: tradeModal.open(chartController ? (chartController.currentTicker || "").replace(/\.IS$/i, "") : "", 0)
                    }
                }
            }

            // 1. KPI Metrik Kartları (4 Adet; dar pencerede 2x2)
            GridLayout {
                Layout.fillWidth: true
                columns: root.width < 980 ? 2 : 4
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd
                uniformCellWidths: true

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiTotalValue
                    value: dashboardController.totalValue
                    changeText: dashboardController.dailyGainLossPct
                    isPositive: dashboardController.isDailyPositive
                    subText: Strings.kpiDailyChange
                    iconName: "banknote"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiDailyGainLoss
                    value: dashboardController.dailyGainLoss
                    changeText: dashboardController.dailyGainLossPct
                    isPositive: dashboardController.isDailyPositive
                    subText: Strings.kpiTodayReturn
                    iconName: "trendingup"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiUnrealizedPL
                    value: dashboardController.totalGainLoss
                    changeText: dashboardController.totalGainLossPct
                    isPositive: dashboardController.isTotalPositive
                    subText: Strings.kpiCostPrefix + dashboardController.totalCost
                    iconName: "linechart"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiCashRatio
                    value: dashboardController.cashBalance
                    changeText: dashboardController.cashRatio
                    isPositive: true
                    subText: dashboardController.holdingsCount + Strings.kpiOpenPositionsSuffix
                    iconName: "portfolio"
                }
            }

            // 2. Varlık dağılımı (sol) + dönemsel getiriler (sağ; haftalık / aylık)
            GridLayout {
                id: midGrid
                readonly property bool stacked: root.width < 1000
                Layout.fillWidth: true
                columns: stacked ? 1 : 2
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd

                AssetAllocationCard {
                    id: allocationCard
                    Layout.fillWidth: midGrid.stacked
                    Layout.preferredWidth: midGrid.stacked ? -1 : 320
                    Layout.preferredHeight: 340
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: Theme.spaceMd

                    MetricCard {
                        Layout.fillWidth: true
                        implicitHeight: 96
                        title: Strings.kpiWeeklyReturn
                        value: dashboardController.weeklyReturnText
                        changeText: Strings.kpiWeeklyBadge
                        isPositive: dashboardController.isWeeklyPositive
                        subText: Strings.kpiPeriodReturnSub
                        iconName: "trendingup"
                    }

                    MetricCard {
                        Layout.fillWidth: true
                        implicitHeight: 96
                        title: Strings.kpiMonthlyReturn
                        value: dashboardController.monthlyReturnText
                        changeText: Strings.kpiMonthlyBadge
                        isPositive: dashboardController.isMonthlyPositive
                        subText: Strings.kpiPeriodReturnSub
                        iconName: "trendingup"
                    }
                }
            }

            // 3. Açık Pozisyonlar Tablosu
            OpenPositionsTable {
                Layout.fillWidth: true
                onTradeRequested: function(ticker, price) {
                    tradeModal.open(ticker, price)
                }
            }
        }
    }

    // --- Modallar & Toast Bildirimi ---
    QuickTradeModal {
        id: tradeModal
    }

    CapitalModal {
        id: capitalModal
    }

    ExcelExportDialog {
        id: excelDialog
        title: Strings.excelDialogTitlePortfolio
        onExportRequested: function(startText, endText, filePath, append) {
            dashboardController.exportToExcelFile(startText, endText, filePath, append)
        }
    }

    ToastNotification {
        id: toast
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: Theme.spaceLg
    }

    // Python Controller Sinyal Bağlantıları
    Connections {
        target: dashboardController

        function onTradeExecuted(success, message) {
            toast.show(message, success)
        }

        function onCapitalUpdated(success, message) {
            toast.show(message, success)
        }

        function onExcelExported(success, message) {
            toast.show(message, success)
        }
    }
}
