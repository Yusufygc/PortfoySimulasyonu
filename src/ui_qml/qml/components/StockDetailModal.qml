import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Item {
    id: root

    // Sinyaller
    signal openChartRequested(string ticker)
    signal openStock360Requested(string ticker)

    visible: (typeof stockDetailController !== "undefined") && stockDetailController.isOpen
    anchors.fill: parent
    z: 998

    // Aktif alt sekme: 0 = İşlem Geçmişi, 1 = Sermaye Artırımları
    property int activeTab: 0

    // Emir Formu Değişkenleri
    property string tradeSide: "BUY"  // "BUY" veya "SELL"
    property int tradeQty: 100
    property real tradePrice: (typeof stockDetailController !== "undefined" && stockDetailController.currentPrice > 0)
                              ? stockDetailController.currentPrice
                              : 10.0

    Connections {
        target: (typeof stockDetailController !== "undefined") ? stockDetailController : null
        function onStockChanged() {
            if (stockDetailController && stockDetailController.currentPrice > 0) {
                root.tradePrice = stockDetailController.currentPrice
                txtPrice.text = stockDetailController.currentPrice.toFixed(2)
            }
        }
        function onTradeExecuted(success, message) {
            localToast.show(message, success)
        }
        function onExcelExported(success, message) {
            localToast.show(message, success)
        }
    }

    onVisibleChanged: {
        if (visible && stockDetailController && stockDetailController.currentPrice > 0) {
            root.tradePrice = stockDetailController.currentPrice
            txtPrice.text = stockDetailController.currentPrice.toFixed(2)
        }
    }

    // Yarı saydam koyu arka plan (Backdrop)
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.05, 0.07, 0.12, 0.75)

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (typeof stockDetailController !== "undefined") {
                    stockDetailController.close()
                }
            }
        }
    }

    // Modal Pencere Gövdesi
    Rectangle {
        id: modalBox
        width: Math.min(parent.width - 64, 1020)
        height: Math.min(parent.height - 48, 740)
        anchors.centerIn: parent
        color: Theme.bgSecondary
        radius: Theme.radiusMd
        border.color: Theme.borderSubtle
        border.width: 1
        clip: true

        // Tıklamaların arkaya geçmesini engelle
        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            // =================================================================
            // 1. ÜST BAŞLIK VE KONTROL BARI
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

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
                            text: (typeof stockDetailController !== "undefined") ? stockDetailController.portfolioName : "Portföy"
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
                RowLayout {
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
                        onClicked: corporateActionDialog.open(stockDetailController.ticker)
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

            // Ayırıcı Çizgi
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderSubtle
            }

            // =================================================================
            // 2. POZİSYON KPI KARTLARI (4 KART)
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

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

            // =================================================================
            // 3. İKİ SÜTUNLU GÖVDE: SOL TABLOLAR & SAĞ HIZLI EMİR FORMU
            // =================================================================
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.spaceMd

                // -------------------------------------------------------------
                // SOL PANEL: TABLAR (İŞLEM GEÇMİŞİ & SERMAYE ARTIRIMLARI)
                // -------------------------------------------------------------
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 620
                    radius: Theme.radiusSm
                    color: Theme.bgCard
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        // Sekme Başlıkları
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Rectangle {
                                height: 32
                                Layout.preferredWidth: 120
                                radius: Theme.radiusSm
                                color: root.activeTab === 0 ? Theme.primary : Theme.bgSecondary

                                Text {
                                    anchors.centerIn: parent
                                    text: Strings.stockDetailTabTrades
                                    color: root.activeTab === 0 ? "#FFFFFF" : Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.DemiBold
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.activeTab = 0
                                }
                            }

                            Rectangle {
                                height: 32
                                Layout.preferredWidth: 140
                                radius: Theme.radiusSm
                                color: root.activeTab === 1 ? Theme.primary : Theme.bgSecondary

                                Text {
                                    anchors.centerIn: parent
                                    text: Strings.stockDetailTabCorpActions
                                    color: root.activeTab === 1 ? "#FFFFFF" : Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.DemiBold
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.activeTab = 1
                                }
                            }

                            Item { Layout.fillWidth: true }
                        }

                        // Tab 1: İşlem Geçmişi Tablosu
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: root.activeTab === 0
                            spacing: 6

                            // Başlık Satırı
                            Rectangle {
                                Layout.fillWidth: true
                                height: 28
                                radius: 4
                                color: Theme.bgSecondary

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8

                                    Text { text: Strings.stockDetailThDate; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                                    Text { text: Strings.stockDetailThTime; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 50 }
                                    Text { text: Strings.stockDetailThType; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 70 }
                                    Text { text: Strings.stockDetailThQty; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                                    Text { text: Strings.stockDetailThPrice; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                                    Text { text: Strings.stockDetailThTotal; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                }
                            }

                            // Liste
                            ListView {
                                id: tradesListView
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: (typeof stockDetailController !== "undefined") ? stockDetailController.tradesList : []
                                spacing: 4

                                delegate: Rectangle {
                                    width: tradesListView.width
                                    height: 32
                                    radius: 4
                                    color: index % 2 === 0 ? Theme.bgSecondary : "transparent"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8

                                        Text { text: modelData.date || ""; color: Theme.textSecondary; font.pixelSize: 11; Layout.preferredWidth: 80 }
                                        Text { text: modelData.time || "-"; color: Theme.textMuted; font.pixelSize: 11; Layout.preferredWidth: 50 }

                                        Rectangle {
                                            Layout.preferredWidth: 56
                                            Layout.preferredHeight: 20
                                            radius: 10
                                            color: modelData.isBuy ? Theme.bullGreenSoft : Theme.bearRedSoft

                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.side || "ALIM"
                                                color: modelData.isBuy ? Theme.bullGreen : Theme.bearRed
                                                font.pixelSize: 10
                                                font.weight: Font.Bold
                                            }
                                        }

                                        Item { Layout.preferredWidth: 14 }

                                        RowLayout {
                                            Layout.preferredWidth: 80
                                            Layout.alignment: Qt.AlignRight
                                            spacing: 4

                                            Text {
                                                text: modelData.quantityStr || ((modelData.quantity || 0) + " Lot")
                                                color: Theme.textPrimary
                                                font.family: Theme.monoFontFamily
                                                font.pixelSize: 11
                                                Layout.fillWidth: true
                                                horizontalAlignment: Text.AlignRight
                                            }

                                            Rectangle {
                                                visible: Boolean(modelData.hasSplit)
                                                width: 14
                                                height: 14
                                                radius: 7
                                                color: Theme.accentSoft
                                                ToolTip.visible: splitMouse.containsMouse
                                                ToolTip.text: modelData.splitNote || ""
                                                ToolTip.delay: 200

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "B"
                                                    color: Theme.accent
                                                    font.pixelSize: 9
                                                    font.weight: Font.Bold
                                                }

                                                MouseArea {
                                                    id: splitMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                }
                                            }
                                        }
                                        Text { text: modelData.priceStr || "₺0.00"; color: Theme.textPrimary; font.family: Theme.monoFontFamily; font.pixelSize: 11; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                                        Text { text: modelData.totalStr || "₺0.00"; color: Theme.textPrimary; font.family: Theme.monoFontFamily; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: tradesListView.count === 0
                                    text: Strings.stockDetailEmptyTrades
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                }
                            }
                        }

                        // Tab 2: Sermaye Artırımları Tablosu
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: root.activeTab === 1
                            spacing: 6

                            // Başlık Satırı
                            Rectangle {
                                Layout.fillWidth: true
                                height: 28
                                radius: 4
                                color: Theme.bgSecondary

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8

                                    Text { text: Strings.stockDetailThDate; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 100 }
                                    Text { text: Strings.stockDetailThType; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 120 }
                                    Text { text: Strings.stockDetailThRatio; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                }
                            }

                            ListView {
                                id: corpListView
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: (typeof stockDetailController !== "undefined") ? stockDetailController.corpActionsList : []
                                spacing: 4

                                delegate: Rectangle {
                                    width: corpListView.width
                                    height: 32
                                    radius: 4
                                    color: index % 2 === 0 ? Theme.bgSecondary : "transparent"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8

                                        Text { text: modelData.date || ""; color: Theme.textSecondary; font.pixelSize: 11; Layout.preferredWidth: 100 }
                                        Text { text: modelData.actionType || ""; color: Theme.textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.preferredWidth: 120 }
                                        Text { text: modelData.ratioStr || "%0.0"; color: Theme.bullGreen; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: corpListView.count === 0
                                    text: Strings.stockDetailEmptyCorp
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                }
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // SAĞ PANEL: HIZLI EMİR FORMU
                // -------------------------------------------------------------
                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Theme.bgCard
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 12

                        Text {
                            text: Strings.stockDetailQuickTrade
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                        }

                        // Alış / Satış Seçim Butonları
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Rectangle {
                                Layout.fillWidth: true
                                height: 34
                                radius: Theme.radiusSm
                                color: root.tradeSide === "BUY" ? Theme.bullGreen : Theme.bgSecondary
                                border.color: Theme.bullGreen
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: "ALIM (BUY)"
                                    color: root.tradeSide === "BUY" ? "#FFFFFF" : Theme.bullGreen
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Bold
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.tradeSide = "BUY"
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 34
                                radius: Theme.radiusSm
                                color: root.tradeSide === "SELL" ? Theme.bearRed : Theme.bgSecondary
                                border.color: Theme.bearRed
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: "SATIM (SELL)"
                                    color: root.tradeSide === "SELL" ? "#FFFFFF" : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Bold
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.tradeSide = "SELL"
                                }
                            }
                        }

                        // Lot Adedi Girişi
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                text: "Lot Adedi:"
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 34
                                radius: Theme.radiusSm
                                color: Theme.bgInput
                                border.color: Theme.borderSubtle
                                border.width: 1

                                TextInput {
                                    id: txtQty
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    text: root.tradeQty.toString()
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    onTextChanged: {
                                        const q = parseInt(text)
                                        if (!isNaN(q) && q > 0) root.tradeQty = q
                                    }
                                }
                            }
                        }

                        // İşlem Fiyatı Girişi
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                text: "Birim Fiyat (₺):"
                                color: Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 34
                                radius: Theme.radiusSm
                                color: Theme.bgInput
                                border.color: Theme.borderSubtle
                                border.width: 1

                                TextInput {
                                    id: txtPrice
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    text: root.tradePrice.toFixed(2)
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.Bold
                                    onTextChanged: {
                                        const p = parseFloat(text.replace(",", "."))
                                        if (!isNaN(p) && p > 0) root.tradePrice = p
                                    }
                                }
                            }
                        }

                        // Toplam Tutar Önizlemesi
                        Rectangle {
                            Layout.fillWidth: true
                            height: 48
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10

                                Text {
                                    text: "Toplam Tutar:"
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }

                                Text {
                                    text: "₺" + (root.tradeQty * root.tradePrice).toLocaleString(Qt.locale("tr_TR"), "f", 2)
                                    color: root.tradeSide === "BUY" ? Theme.bullGreen : Theme.bearRed
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.weight: Font.Bold
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        // Emri Gönder Butonu
                        Rectangle {
                            Layout.fillWidth: true
                            height: 40
                            radius: Theme.radiusSm
                            color: root.tradeSide === "BUY" ? Theme.bullGreen : Theme.bearRed

                            Text {
                                anchors.centerIn: parent
                                text: (root.tradeSide === "BUY" ? "ALIM EMRİNİ ONAYLA" : "SATIM EMRİNİ ONAYLA")
                                color: "#FFFFFF"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof stockDetailController !== "undefined") {
                                        stockDetailController.submitTrade(
                                            root.tradeSide,
                                            root.tradeQty,
                                            root.tradePrice,
                                            ""
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    CorporateActionDialog {
        id: corporateActionDialog
        onApplied: function(message) {
            localToast.show(message, true)
            if (typeof stockDetailController !== "undefined") {
                stockDetailController.refreshData()
            }
        }
    }

    // Modal İçi Toast Bildirimi
    ToastNotification {
        id: localToast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 32
        z: 999
    }
}
