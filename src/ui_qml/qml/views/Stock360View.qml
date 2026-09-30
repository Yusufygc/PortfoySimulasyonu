import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null

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
            id: mainColumn
            width: mainScrollView.availableWidth
            spacing: Theme.spaceMd

            // ---------------------------------------------------------
            // 1. ÜST ARAÇ ÇUBUĞU & ARAMA & HIZLI HİSSE BUTONLARI
            // ---------------------------------------------------------
            ModernCard {
                Layout.fillWidth: true
                implicitHeight: topBarCol.implicitHeight + Theme.spaceMd * 2

                ColumnLayout {
                    id: topBarCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    // Üst Satır: Arama Kutusu ve Aksiyon Butonları
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        // Arama Girişi
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 220
                            Layout.maximumWidth: 380
                            implicitHeight: 36
                            radius: Theme.radiusSm
                            color: Theme.bgInput
                            border.color: searchInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8

                                ModernIcon {
                                    name: "search"
                                    size: 14
                                    color: Theme.textMuted
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                TextInput {
                                    id: searchInput
                                    Layout.fillWidth: true
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textPrimary
                                    selectByMouse: true
                                    clip: true
                                    text: ""

                                    Text {
                                        text: Strings.searchStockPlaceholder
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        color: Theme.textMuted
                                        visible: !searchInput.text && !searchInput.activeFocus
                                    }

                                    onAccepted: {
                                        if (text.trim() !== "" && root.ctrl) {
                                            root.ctrl.searchTicker(text.trim())
                                        }
                                    }
                                }

                                Rectangle {
                                    visible: searchInput.text !== ""
                                    width: 16
                                    height: 16
                                    radius: 8
                                    color: Theme.bgCardHover
                                    Layout.alignment: Qt.AlignVCenter

                                    ModernIcon {
                                        anchors.centerIn: parent
                                        name: "close"
                                        size: 10
                                        color: Theme.textMuted
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: searchInput.text = ""
                                    }
                                }
                            }
                        }

                        // Analiz Et Butonu
                        ModernButton {
                            text: Strings.btnAnalyze
                            iconName: "target"
                            variant: "primary"
                            onClicked: {
                                if (searchInput.text.trim() !== "" && root.ctrl) {
                                    root.ctrl.searchTicker(searchInput.text.trim())
                                }
                            }
                        }

                        // Verileri Yenile Butonu
                        ModernButton {
                            text: Strings.btnRefresh
                            iconName: "refresh"
                            onClicked: {
                                if (root.ctrl) {
                                    root.ctrl.refreshData()
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }

                        // TradingView Grafiğinde Aç Butonu
                        ModernButton {
                            text: Strings.btnOpenInTradingView
                            iconName: "linechart"
                            onClicked: {
                                if (typeof chartController !== "undefined" && chartController && root.ctrl) {
                                    chartController.loadStock(root.ctrl.currentTicker)
                                }
                                if (typeof shellController !== "undefined" && shellController) {
                                    shellController.navigateTo(0)
                                }
                            }
                        }
                    }

                    // Alt Satır: Hızlı Hisse Seçimi (Flickable)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Text {
                            text: Strings.quickStocksLabel
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                            color: Theme.textMuted
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Flickable {
                            Layout.fillWidth: true
                            implicitHeight: 28
                            contentWidth: pillRow.implicitWidth
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds

                            Row {
                                id: pillRow
                                spacing: 6

                                Repeater {
                                    model: root.ctrl ? root.ctrl.availableStocks : []

                                    Rectangle {
                                        id: stockPill
                                        property bool isCurrent: (root.ctrl && root.ctrl.currentTicker === modelData)
                                        implicitWidth: pillText.implicitWidth + 14
                                        implicitHeight: 26
                                        radius: Theme.radiusSm
                                        color: isCurrent
                                               ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2)
                                               : (pillMouse.containsMouse ? Theme.bgCardHover : Theme.bgInput)
                                        border.color: isCurrent ? Theme.accent : Theme.borderSubtle
                                        border.width: 1

                                        Behavior on color { ColorAnimation { duration: 120 } }

                                        Text {
                                            id: pillText
                                            anchors.centerIn: parent
                                            text: modelData
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            font.weight: stockPill.isCurrent ? Font.Bold : Font.Normal
                                            color: stockPill.isCurrent ? Theme.accent : Theme.textSecondary
                                        }

                                        MouseArea {
                                            id: pillMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (root.ctrl) {
                                                    root.ctrl.searchTicker(modelData)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ---------------------------------------------------------
            // 2. HERO HEADER — GENEL BAKIŞ & FİYAT KARTI
            // ---------------------------------------------------------
            ModernCard {
                Layout.fillWidth: true
                implicitHeight: 128

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceLg

                    // Sol Taraf: Ticker, Şirket Unvanı, Sektör
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        RowLayout {
                            spacing: Theme.spaceSm

                            Text {
                                text: root.ctrl ? root.ctrl.currentTicker : "—"
                                font.family: Theme.fontFamily
                                font.pixelSize: 26
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                            }

                            // Sektör Rozeti
                            Rectangle {
                                implicitWidth: sectorLabel.implicitWidth + 12
                                implicitHeight: 22
                                radius: 11
                                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12)
                                Layout.alignment: Qt.AlignVCenter

                                Text {
                                    id: sectorLabel
                                    anchors.centerIn: parent
                                    text: root.ctrl ? root.ctrl.sector : ""
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.Medium
                                    color: Theme.accent
                                }
                            }

                            // Yükleniyor Bildirimi
                            Rectangle {
                                visible: root.ctrl && root.ctrl.isLoading
                                implicitWidth: loadingLabel.implicitWidth + 12
                                implicitHeight: 22
                                radius: 11
                                color: Qt.rgba(Theme.accentWarm.r, Theme.accentWarm.g, Theme.accentWarm.b, 0.18)
                                Layout.alignment: Qt.AlignVCenter

                                Text {
                                    id: loadingLabel
                                    anchors.centerIn: parent
                                    text: "Veriler yükleniyor..."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.accentWarm
                                }
                            }
                        }

                        Text {
                            text: root.ctrl ? root.ctrl.companyName : ""
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textSecondary
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        // Alt Bilgiler: Hacim & Fiyat Tarihi
                        RowLayout {
                            spacing: Theme.spaceMd
                            Layout.topMargin: 4

                            Row {
                                spacing: 4
                                Text {
                                    text: Strings.labelVolume + ":"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }
                                Text {
                                    text: root.ctrl ? root.ctrl.volume : "—"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                }
                            }

                            Row {
                                spacing: 4
                                Text {
                                    text: Strings.labelPriceDate + ":"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }
                                Text {
                                    text: root.ctrl ? root.ctrl.lastPriceDate : "—"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                }
                            }
                        }
                    }

                    // Sağ Taraf: Son Fiyat, Günlük Değişim ve 52 Haftalık Aralık
                    ColumnLayout {
                        Layout.preferredWidth: 320
                        spacing: 4
                        Layout.alignment: Qt.AlignRight

                        RowLayout {
                            Layout.alignment: Qt.AlignRight
                            spacing: Theme.spaceSm

                            Text {
                                text: root.ctrl ? root.ctrl.lastPrice : "—"
                                font.family: Theme.fontFamily
                                font.pixelSize: 26
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                            }

                            // Günlük Değişim Rozeti
                            Rectangle {
                                implicitWidth: changeRow.implicitWidth + 12
                                implicitHeight: 24
                                radius: 12
                                color: (root.ctrl && root.ctrl.isDailyPositive)
                                       ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.15)
                                       : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.15)
                                Layout.alignment: Qt.AlignVCenter

                                RowLayout {
                                    id: changeRow
                                    anchors.centerIn: parent
                                    spacing: 4

                                    ModernIcon {
                                        name: (root.ctrl && root.ctrl.isDailyPositive)
                                              ? "trendingup"
                                              : "trendingdown"
                                        size: 12
                                        color: (root.ctrl && root.ctrl.isDailyPositive)
                                               ? Theme.bullGreen
                                               : Theme.bearRed
                                    }

                                    Text {
                                        text: root.ctrl ? root.ctrl.dailyChange : "%0.00"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                        color: (root.ctrl && root.ctrl.isDailyPositive)
                                               ? Theme.bullGreen
                                               : Theme.bearRed
                                    }
                                }
                            }
                        }

                        // 52 Haftalık Aralık Çubuğu
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: 4
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "52H En Düşük: " + (root.ctrl ? root.ctrl.week52Low : "—")
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    color: Theme.textMuted
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: "52H En Yüksek: " + (root.ctrl ? root.ctrl.week52High : "—")
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    color: Theme.textMuted
                                }
                            }

                            // Progress Bar
                            Rectangle {
                                Layout.fillWidth: true
                                height: 5
                                radius: 2.5
                                color: Theme.bgInput

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    width: Math.max(8, parent.width * (root.ctrl ? root.ctrl.week52RangePct : 0.5))
                                    radius: 2.5
                                    color: Theme.accent
                                }
                            }
                        }
                    }
                }
            }

            // ---------------------------------------------------------
            // 3. FİNANSAL DEĞERLEME & RASYOLAR (GRID)
            // ---------------------------------------------------------
            GridLayout {
                Layout.fillWidth: true
                columns: Math.max(2, Math.min(4, Math.floor(mainColumn.width / 200)))
                rowSpacing: Theme.spaceSm
                columnSpacing: Theme.spaceSm

                RatioCard {
                    title: Strings.ratioPE
                    value: root.ctrl ? root.ctrl.peRatio : "—"
                    subtitle: Strings.ratioPEDesc
                    iconName: "scale"
                    accentColor: Theme.accent
                    badgeText: "Değerleme"
                }

                RatioCard {
                    title: Strings.ratioPB
                    value: root.ctrl ? root.ctrl.pbRatio : "—"
                    subtitle: Strings.ratioPBDesc
                    iconName: "shield-check"
                    accentColor: "#8b5cf6"
                    badgeText: "Özkaynak"
                }

                RatioCard {
                    title: Strings.ratioEvEbitda
                    value: root.ctrl ? root.ctrl.evEbitda : "—"
                    subtitle: Strings.ratioEvEbitdaDesc
                    iconName: "activity"
                    accentColor: "#06b6d4"
                    badgeText: "Operasyonel"
                }

                RatioCard {
                    title: Strings.ratioDivYield
                    value: root.ctrl ? root.ctrl.divYield : "—"
                    subtitle: Strings.ratioDivYieldDesc
                    iconName: "coins"
                    accentColor: Theme.bullGreen
                    badgeText: "Temettü"
                }

                RatioCard {
                    title: "ROE"
                    value: root.ctrl ? root.ctrl.roe : "—"
                    subtitle: Strings.ratioROEDesc
                    iconName: "trendingup"
                    accentColor: Theme.bullGreen
                    badgeText: "Kârlılık"
                }

                RatioCard {
                    title: Strings.ratioNetDebtEbitda
                    value: root.ctrl ? root.ctrl.netDebtEbitda : "—"
                    subtitle: Strings.ratioNetDebtEbitdaDesc
                    iconName: "banknote"
                    accentColor: "#f59e0b"
                    badgeText: "Kaldıraç"
                }

                RatioCard {
                    title: Strings.ratioPiotroski
                    value: root.ctrl ? root.ctrl.piotroskiScore : "—"
                    subtitle: Strings.ratioPiotroskiDesc
                    iconName: "shield-check"
                    accentColor: Theme.accent
                    badgeText: "F-Score"
                }

                RatioCard {
                    title: Strings.ratioCurrentRatio
                    value: root.ctrl ? root.ctrl.currentRatio : "—"
                    subtitle: Strings.ratioCurrentRatioDesc
                    iconName: "zap"
                    accentColor: "#10b981"
                    badgeText: "Likidite"
                }
            }

            // ---------------------------------------------------------
            // 4. ORTA BÖLÜM: ÇEYREKLİK BİLANÇO & GELİR TABLOSU + KAP ORTAKLIK
            // ---------------------------------------------------------
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

                // Çeyreklik Bilanço ve Gelir Tablosu Çubuk Grafiği
                FinancialBarChart {
                    Layout.fillWidth: true
                    Layout.preferredWidth: (mainColumn.width - Theme.spaceMd) * 0.62
                }

                // KAP Ortaklık Yapısı & Halka Açıklık Oranı
                ShareholderPieCard {
                    Layout.fillWidth: true
                    Layout.preferredWidth: (mainColumn.width - Theme.spaceMd) * 0.38
                }
            }

            // ---------------------------------------------------------
            // 5. TEKNİK SEVİYELER & DESTEK / DİRENÇ KARTI
            // ---------------------------------------------------------
            ModernCard {
                Layout.fillWidth: true
                implicitHeight: techCol.implicitHeight + Theme.spaceMd * 2

                ColumnLayout {
                    id: techCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    // Başlık & Trend Durumu Rozeti
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        RowLayout {
                            spacing: 6
                            Layout.fillWidth: true

                            Rectangle {
                                width: 18
                                height: 18
                                radius: Theme.radiusSm
                                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                                Layout.alignment: Qt.AlignVCenter

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "target"
                                    size: 11
                                    color: Theme.accent
                                }
                            }

                            Text {
                                text: Strings.technicalTitle
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                                font.letterSpacing: 0.5
                            }
                        }

                        // Trend Durumu Rozeti
                        Rectangle {
                            implicitWidth: trendLabel.implicitWidth + 14
                            implicitHeight: 22
                            radius: 11
                            color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                            Layout.alignment: Qt.AlignVCenter

                            Text {
                                id: trendLabel
                                anchors.centerIn: parent
                                text: root.ctrl ? root.ctrl.trendStatus : "Dengeli"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.DemiBold
                                color: Theme.accent
                            }
                        }
                    }

                    // Separator
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.borderSubtle
                    }

                    // 4 Sütunlu Teknik Metrikler
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        // 1. RSI (14)
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 64
                            radius: Theme.radiusSm
                            color: Theme.bgInput
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2

                                Text {
                                    text: Strings.labelRSI
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }

                                RowLayout {
                                    spacing: 6
                                    Text {
                                        text: root.ctrl ? root.ctrl.rsi14 : "—"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontMd
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                    }
                                    Text {
                                        text: root.ctrl ? root.ctrl.rsiStatus : ""
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        color: Theme.accent
                                    }
                                }
                            }
                        }

                        // 2. MACD
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 64
                            radius: Theme.radiusSm
                            color: Theme.bgInput
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2

                                Text {
                                    text: Strings.labelMACD
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }

                                RowLayout {
                                    spacing: 4
                                    Text {
                                        text: "Çizgi: " + (root.ctrl ? root.ctrl.macdLine : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                    }
                                    Text {
                                        text: "• Sinyal: " + (root.ctrl ? root.ctrl.macdSignal : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        color: Theme.textSecondary
                                    }
                                }
                            }
                        }

                        // 3. SMA & EMA
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 64
                            radius: Theme.radiusSm
                            color: Theme.bgInput
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2

                                Text {
                                    text: "SMA 50 / 200 & EMA 20"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }

                                RowLayout {
                                    spacing: 4
                                    Text {
                                        text: (root.ctrl ? root.ctrl.sma50 : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Bold
                                        color: Theme.accent
                                    }
                                    Text {
                                        text: "/ " + (root.ctrl ? root.ctrl.sma200 : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        color: Theme.textSecondary
                                    }
                                }
                            }
                        }

                        // 4. Destek & Direnç
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 64
                            radius: Theme.radiusSm
                            color: Theme.bgInput
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 2

                                Text {
                                    text: Strings.labelSupport + " / " + Strings.labelResistance
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                }

                                RowLayout {
                                    spacing: 4
                                    Text {
                                        text: (root.ctrl ? root.ctrl.support : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Bold
                                        color: Theme.bullGreen
                                    }
                                    Text {
                                        text: "/ " + (root.ctrl ? root.ctrl.resistance : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Bold
                                        color: Theme.bearRed
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
