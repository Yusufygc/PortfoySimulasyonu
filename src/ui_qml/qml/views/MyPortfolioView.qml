import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    // "Fiyatları Yenile" düğmesine basıldı: sonuç bildirimi gösterilir (otomatik yenileme sessizdir)
    property bool manualRefresh: false

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
                columns: root.width < 1500 ? 1 : 2
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
                    Layout.alignment: root.width < 1500 ? Qt.AlignLeft : Qt.AlignRight
                    Layout.fillWidth: root.width < 1500
                    spacing: Theme.spaceSm

                    // TRY / USD gösterim anahtarı
                    Row {
                        spacing: 2
                        ModernButton {
                            text: Strings.currencyTRY
                            variant: myPortfolioController.displayCurrency === "TRY" ? "primary" : "ghost"
                            onClicked: myPortfolioController.setDisplayCurrency("TRY")
                        }
                        ModernButton {
                            text: Strings.currencyUSD
                            variant: myPortfolioController.displayCurrency === "USD" ? "primary" : "ghost"
                            onClicked: myPortfolioController.setDisplayCurrency("USD")
                        }
                    }

                    // Varlık fiyatlarını ve BIST fiyatlarını şimdi yenile
                    ModernButton {
                        text: Strings.btnRefresh
                        iconName: "refresh"
                        variant: "ghost"
                        enabled: !assetsController.busy
                        onClicked: {
                            root.manualRefresh = true
                            assetsController.refreshPrices()
                            if (typeof priceRefreshController !== "undefined") priceRefreshController.refreshNow()
                        }
                    }

                    // Varlık Ekle / Varlık İşlemi (BIST dışı)
                    ModernButton {
                        text: Strings.btnAddAsset
                        iconName: "coins"
                        variant: "secondary"
                        onClicked: assetAddModal.open()
                    }

                    ModernButton {
                        text: Strings.btnAssetTrade
                        iconName: "trade"
                        variant: "secondary"
                        onClicked: assetTradeModal.open(0)
                    }

                    // Döviz Al/Sat (ortak nakit havuzu: TL <-> USD)
                    ModernButton {
                        text: Strings.btnFx
                        iconName: "banknote"
                        variant: "secondary"
                        onClicked: fxModal.open()
                    }

                    // Sermaye Yönetimi Butonu (BIST nakdi)
                    ModernButton {
                        text: Strings.btnCapital
                        iconName: "capital"
                        variant: "secondary"
                        onClicked: capitalModal.open()
                    }

                    // Excel Raporu Butonu (BIST portföyü)
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

                    // Hızlı Al/Sat Butonu (BIST)
                    ModernButton {
                        text: Strings.btnQuickTrade
                        iconName: "zap"
                        variant: "primary"
                        onClicked: tradeModal.open(chartController ? (chartController.currentTicker || "").replace(/\.IS$/i, "") : "", 0)
                    }
                }
            }

            // Uyarılar: değerlenemeyen pozisyon ve USD kuru
            Rectangle {
                visible: myPortfolioController.isPartial
                Layout.fillWidth: true
                implicitHeight: partialText.implicitHeight + Theme.spaceMd
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.warning
                border.width: 1

                Text {
                    id: partialText
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    text: Strings.myPortfolioPartialNote + myPortfolioController.unpricedSymbols.join(", ")
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.warning
                    wrapMode: Text.WordWrap
                }
            }

            Text {
                visible: myPortfolioController.staleSymbols.length > 0
                Layout.fillWidth: true
                text: Strings.myPortfolioStaleNote + myPortfolioController.staleSymbols.join(", ")
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.warning
                wrapMode: Text.WordWrap
            }

            Text {
                visible: myPortfolioController.displayUnavailable
                text: Strings.myPortfolioUsdUnavailable
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.warning
                Layout.fillWidth: true
            }

            Text {
                visible: myPortfolioController.displayCurrency === "USD" && !myPortfolioController.displayUnavailable
                text: Strings.myPortfolioUsdRateNote + myPortfolioController.usdRate
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.fillWidth: true
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
                    value: myPortfolioController.totalValue
                    changeText: myPortfolioController.dailyGainPct
                    isPositive: myPortfolioController.isDailyPositive
                    subText: myPortfolioController.isMarketDayClosed ? Strings.kpiLastSessionChange : Strings.kpiDailyChange
                    iconName: "banknote"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiDailyGainLoss
                    value: myPortfolioController.dailyGain
                    changeText: myPortfolioController.dailyGainPct
                    isPositive: myPortfolioController.isDailyPositive
                    subText: myPortfolioController.isMarketDayClosed ? Strings.kpiLastSessionReturn : Strings.kpiTodayReturn
                    iconName: "trendingup"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiUnrealizedPL
                    value: myPortfolioController.unrealizedPL
                    changeText: myPortfolioController.unrealizedPLPct
                    isPositive: myPortfolioController.isPLPositive
                    subText: Strings.kpiCostPrefix + myPortfolioController.totalCost
                    iconName: "linechart"
                }

                MetricCard {
                    Layout.fillWidth: true
                    title: Strings.kpiCashRatio
                    value: myPortfolioController.cashBalance
                    changeText: myPortfolioController.cashRatio
                    isPositive: true
                    subText: (myPortfolioController.hasUsdCash ? Strings.kpiUsdCashPrefix + myPortfolioController.usdCashBalance + " - " : "")
                             + myPortfolioController.holdingsCount + Strings.kpiOpenPositionsSuffix
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
                    slices: myPortfolioController.allocationSlices
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
            HoldingsTable {
                Layout.fillWidth: true
                onTradeRequested: function(ticker) {
                    tradeModal.open(ticker, 0)
                }
                onAssetTradeRequested: function(assetId) {
                    assetTradeModal.open(assetId)
                }
                onAssetRemoveRequested: function(assetId) {
                    assetsController.removeAsset(assetId)
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

    AssetAddModal {
        id: assetAddModal
    }

    AssetTradeModal {
        id: assetTradeModal
    }

    FxConvertModal {
        id: fxModal
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

    // BIST işlem ve sermaye değişiklikleri birleşik özeti yeniden okutur
    Connections {
        target: dashboardController

        function onTradeExecuted(success, message) {
            toast.show(message, success)
            if (success) myPortfolioController.reload()
        }

        function onCapitalUpdated(success, message) {
            toast.show(message, success)
            if (success) myPortfolioController.reload()
        }

        function onExcelExported(success, message) {
            toast.show(message, success)
        }
    }

    // Döviz Al/Sat sonuçları
    Connections {
        target: cashPoolController

        function onNotify(success, message) { toast.show(message, success) }
    }

    // Varlık defteri sonuçları; otomatik fiyat yenilemesi yalnızca elle istendiğinde bildirilir
    Connections {
        target: assetsController

        function onAssetAdded(success, message) { toast.show(message, success) }
        function onTradeRecorded(success, message) { toast.show(message, success) }
        function onAssetRemoved(success, message) { toast.show(message, success) }
        function onPricesRefreshed(success, message) {
            if (root.manualRefresh || !success) toast.show(message, success)
            root.manualRefresh = false
        }
    }
}
