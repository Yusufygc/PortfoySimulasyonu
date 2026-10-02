import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null

    Connections {
        target: root.ctrl
        function onViewModeChanged() {
            if (mainScrollView && mainScrollView.contentItem) {
                mainScrollView.contentItem.contentY = 0;
            }
        }
    }

    Component.onCompleted: {
        if (root.ctrl && typeof root.ctrl.ensureLoaded === "function") {
            root.ctrl.ensureLoaded();
        }
    }

    ScrollView {
        id: mainScrollView
        anchors.fill: parent
        clip: true
        contentHeight: mainColumn.childrenRect.height + Theme.spaceMd * 2
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
            objectName: "mainColumn"
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
                                            text: (modelData || "").replace(/\.IS$/i, "")
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
            // 2. GÖRÜNÜM MODU SEÇİCİ SEKME BARI
            // ---------------------------------------------------------
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 46
                radius: Theme.radiusMd
                color: Theme.bgCard
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 4
                    spacing: 6

                    // Sekme 0: Genel Bakış & Özet
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radiusSm
                        color: (root.ctrl && root.ctrl.viewMode === 0) ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15) : "transparent"
                        border.color: (root.ctrl && root.ctrl.viewMode === 0) ? Theme.accent : "transparent"
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 8

                            ModernIcon {
                                name: "target"
                                size: 14
                                color: (root.ctrl && root.ctrl.viewMode === 0) ? Theme.accent : Theme.textMuted
                            }

                            Text {
                                text: Strings.tabOverviewAndCharts
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: (root.ctrl && root.ctrl.viewMode === 0) ? Font.Bold : Font.Normal
                                color: (root.ctrl && root.ctrl.viewMode === 0) ? Theme.accent : Theme.textSecondary
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.ctrl) root.ctrl.setViewMode(0)
                            }
                        }
                    }

                    // Sekme 1: Kapsamlı Bilanço & Finansal Tablolar
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radiusSm
                        color: (root.ctrl && root.ctrl.viewMode === 1) ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15) : "transparent"
                        border.color: (root.ctrl && root.ctrl.viewMode === 1) ? Theme.accent : "transparent"
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 8

                            ModernIcon {
                                name: "layers"
                                size: 14
                                color: (root.ctrl && root.ctrl.viewMode === 1) ? Theme.accent : Theme.textMuted
                            }

                            Text {
                                text: Strings.tabFullFinancials
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: (root.ctrl && root.ctrl.viewMode === 1) ? Font.Bold : Font.Normal
                                color: (root.ctrl && root.ctrl.viewMode === 1) ? Theme.accent : Theme.textSecondary
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.ctrl) root.ctrl.setViewMode(1)
                            }
                        }
                    }

                    // Sekme 2: KAP Ortaklık Tarihçesi
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radiusSm
                        color: (root.ctrl && root.ctrl.viewMode === 2) ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15) : "transparent"
                        border.color: (root.ctrl && root.ctrl.viewMode === 2) ? Theme.accent : "transparent"
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 8

                            ModernIcon {
                                name: "history"
                                size: 14
                                color: (root.ctrl && root.ctrl.viewMode === 2) ? Theme.accent : Theme.textMuted
                            }

                            Text {
                                text: Strings.tabShareholdersTimeline
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: (root.ctrl && root.ctrl.viewMode === 2) ? Font.Bold : Font.Normal
                                color: (root.ctrl && root.ctrl.viewMode === 2) ? Theme.accent : Theme.textSecondary
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.ctrl) root.ctrl.setViewMode(2)
                            }
                        }
                    }
                }
            }

            // ---------------------------------------------------------
            // 3. ŞİRKET BİLGİ & FİYAT HERO KARTI (HER MODDA GÖRÜNÜR)
            // ---------------------------------------------------------
            ModernCard {
                Layout.fillWidth: true
                implicitHeight: heroCol.implicitHeight + Theme.spaceMd * 2

                ColumnLayout {
                    id: heroCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        // Sol: Sembol & Şirket Adı & Sektör
                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true

                            RowLayout {
                                spacing: Theme.spaceSm

                                Text {
                                    text: root.ctrl ? (root.ctrl.currentTicker || "—").replace(/\.IS$/i, "") : "—"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXl
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }

                                Rectangle {
                                    implicitWidth: sectorBadgeText.implicitWidth + 12
                                    implicitHeight: 20
                                    radius: Theme.radiusSm
                                    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12)
                                    border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.25)
                                    border.width: 1
                                    Layout.alignment: Qt.AlignVCenter

                                    Text {
                                        id: sectorBadgeText
                                        anchors.centerIn: parent
                                        text: root.ctrl ? root.ctrl.sector : "—"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        color: Theme.accent
                                    }
                                }
                            }

                            Text {
                                text: root.ctrl ? root.ctrl.companyName : "—"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.maximumWidth: 400
                            }
                        }

                        Item { Layout.fillWidth: true }

                        // Sağ: Canlı / Son Fiyat ve Günlük Değişim
                        ColumnLayout {
                            spacing: 2
                            Layout.alignment: Qt.AlignRight

                            RowLayout {
                                spacing: 8
                                Layout.alignment: Qt.AlignRight

                                Text {
                                    text: root.ctrl ? root.ctrl.lastPrice : "₺0.00"
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontXl
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }

                                Rectangle {
                                    implicitWidth: changeRow.implicitWidth + 12
                                    implicitHeight: 24
                                    radius: Theme.radiusSm
                                    color: (root.ctrl && root.ctrl.isDailyPositive)
                                           ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.15)
                                           : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.15)
                                    border.color: (root.ctrl && root.ctrl.isDailyPositive)
                                                  ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.3)
                                                  : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.3)
                                    border.width: 1
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
                                        text: Strings.stock360Low52Prefix + (root.ctrl ? root.ctrl.week52Low : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        color: Theme.textMuted
                                    }
                                    Item { Layout.fillWidth: true }
                                    Text {
                                        text: Strings.stock360High52Prefix + (root.ctrl ? root.ctrl.week52High : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        color: Theme.textMuted
                                    }
                                }

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
            }

            // =========================================================
            // DİNAMİK GÖRÜNÜM MODU LOADER (0: Genel Bakış, 1: Bilanço, 2: KAP)
            // =========================================================
            Loader {
                id: viewModeLoader
                objectName: "viewModeLoader"
                Layout.fillWidth: true
                height: item ? item.implicitHeight : 0
                Layout.preferredHeight: height
                sourceComponent: {
                    var m = (root.ctrl) ? root.ctrl.viewMode : 0;
                    if (m === 1) return financialsComponent;
                    if (m === 2) return shareholdersComponent;
                    return overviewComponent;
                }
            }
        } // mainColumn sonu
    } // mainScrollView sonu

    // =========================================================
    // GÖRÜNÜM MODU 0: GENEL BAKIŞ & ÖZET KARTLAR
    // =========================================================
    Component {
        id: overviewComponent

        ColumnLayout {
            id: overviewSection
            width: viewModeLoader.width
            spacing: Theme.spaceMd

            // 4. ÖNEMLİ DEĞERLEME VE FİNANSAL RASYOLAR (8'Lİ GRID)
            GridLayout {
                Layout.fillWidth: true
                columns: 4
                rowSpacing: Theme.spaceSm
                columnSpacing: Theme.spaceSm

                RatioCard {
                    title: Strings.ratioPE
                    value: root.ctrl ? root.ctrl.peRatio : "—"
                    subtitle: Strings.ratioPEDesc
                    iconName: "coins"
                    accentColor: Theme.accent
                    badgeText: Strings.badgeValuation
                }

                RatioCard {
                    title: Strings.ratioPB
                    value: root.ctrl ? root.ctrl.pbRatio : "—"
                    subtitle: Strings.ratioPBDesc
                    iconName: "scale"
                    accentColor: "#8b5cf6"
                    badgeText: Strings.badgeMultiple
                }

                RatioCard {
                    title: Strings.ratioEvEbitda
                    value: root.ctrl ? root.ctrl.evEbitda : "—"
                    subtitle: Strings.ratioEvEbitdaDesc
                    iconName: "activity"
                    accentColor: "#06b6d4"
                    badgeText: Strings.badgeOperational
                }

                RatioCard {
                    title: Strings.ratioDivYield
                    value: root.ctrl ? root.ctrl.divYield : "—"
                    subtitle: Strings.ratioDivYieldDesc
                    iconName: "wallet"
                    accentColor: "#ec4899"
                    badgeText: Strings.badgeDividend
                }

                RatioCard {
                    title: Strings.ratioROE
                    value: root.ctrl ? root.ctrl.roe : "—"
                    subtitle: Strings.ratioROEDesc
                    iconName: "trendingup"
                    accentColor: Theme.bullGreen
                    badgeText: Strings.badgeProfitability
                }

                RatioCard {
                    title: Strings.ratioNetDebtEbitda
                    value: root.ctrl ? root.ctrl.netDebtEbitda : "—"
                    subtitle: Strings.ratioNetDebtEbitdaDesc
                    iconName: "banknote"
                    accentColor: "#f59e0b"
                    badgeText: Strings.badgeLeverage
                }

                RatioCard {
                    title: Strings.ratioPiotroski
                    value: root.ctrl ? root.ctrl.piotroskiScore : "—"
                    subtitle: Strings.ratioPiotroskiDesc
                    iconName: "shield-check"
                    accentColor: Theme.accent
                    badgeText: Strings.badgeFScore
                }

                RatioCard {
                    title: Strings.ratioCurrentRatio
                    value: root.ctrl ? root.ctrl.currentRatio : "—"
                    subtitle: Strings.ratioCurrentRatioDesc
                    iconName: "zap"
                    accentColor: "#10b981"
                    badgeText: Strings.badgeLiquidity
                }
            }

            // 5. ORTA BÖLÜM: FİNTECH GELİR GRAFİĞİ + KAP ORTAKLIK
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

                // Çeyreklik Gelir ve Kârlılık Grafiği (Fintech)
                FintechRevenueChart {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 620
                    Layout.minimumWidth: 380
                }

                // KAP Ortaklık Yapısı & Halka Açıklık Oranı
                ShareholderPieCard {
                    fullView: false
                    Layout.fillWidth: true
                    Layout.preferredWidth: 380
                    Layout.minimumWidth: 300
                }
            }

            // 6. TEKNİK SEVİYELER & DESTEK / DİRENÇ KARTI
            ModernCard {
                Layout.fillWidth: true
                implicitHeight: techCol.implicitHeight + Theme.spaceMd * 2

                ColumnLayout {
                    id: techCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

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

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.borderSubtle
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        // RSI (14)
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
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                    }

                                    Rectangle {
                                        implicitWidth: rsiStatusTxt.implicitWidth + 8
                                        implicitHeight: 16
                                        radius: 3
                                        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                                        Text {
                                            id: rsiStatusTxt
                                            anchors.centerIn: parent
                                            text: root.ctrl ? root.ctrl.rsiStatus : "Nötr"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 9
                                            font.weight: Font.DemiBold
                                            color: Theme.accent
                                        }
                                    }
                                }
                            }
                        }

                        // MACD Sinyal
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
                                        text: (root.ctrl ? root.ctrl.macdLine : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        font.weight: Font.Bold
                                        color: Theme.accent
                                    }
                                    Text {
                                        text: "/ " + (root.ctrl ? root.ctrl.macdSignal : "—")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontXs
                                        color: Theme.textSecondary
                                    }
                                }
                            }
                        }

                        // SMA 50 / 200
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
                                    text: Strings.labelMovingAverages
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

                        // Destek & Direnç
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

    // =========================================================
    // GÖRÜNÜM MODU 1: FİNANSAL PERFORMANS & KAPSAMLI BİLANÇO
    // =========================================================
    Component {
        id: financialsComponent

        ColumnLayout {
            id: financialsSection
            width: viewModeLoader.width
            spacing: Theme.spaceMd

            // 1. Çeyreklik Gelir ve Kârlılık Gelişim Grafiği (Fintech Çift Eksen)
            FintechRevenueChart {
                Layout.fillWidth: true
            }

            // 2. Kârlılık Anatomisi (DuPont ROE) ve Serbest Nakit Akışı (FCF) Kartları
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

                FintechDuPontCard {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 550
                    Layout.minimumWidth: 360
                }

                FintechCashFlowCard {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 450
                    Layout.minimumWidth: 320
                }
            }

            // 3. Profesyonel Fintech Tabloları (Bilanço, Gelir, Nakit Akış Tablosu)
            FintechStatementsTable {
                Layout.fillWidth: true
            }
        }
    }

    // =========================================================
    // GÖRÜNÜM MODU 2: KAP ORTAKLIK TARİHÇESİ VE ZAMAN ÇİZELGESİ
    // =========================================================
    Component {
        id: shareholdersComponent

        ColumnLayout {
            id: shareholdersSection
            width: viewModeLoader.width
            spacing: Theme.spaceMd

            // 1. ÜST KPI STRIP (4 RASYONEL KART)
            GridLayout {
                Layout.fillWidth: true
                columns: 4
                rowSpacing: Theme.spaceSm
                columnSpacing: Theme.spaceSm

                // Kart 1: Ödenmiş Sermaye
                RatioCard {
                    title: Strings.labelPaidCapital
                    value: root.ctrl ? root.ctrl.paidCapital : "—"
                    subtitle: Strings.labelPaidCapitalDesc
                    iconName: "coins"
                    accentColor: Theme.accent
                    badgeText: Strings.badgeNominal
                }

                // Kart 2: Fiili Dolaşımdaki Paylar
                RatioCard {
                    title: Strings.labelFreeFloat
                    value: root.ctrl ? root.ctrl.freeFloatRatio : "—"
                    subtitle: Strings.labelFreeFloatDesc
                    iconName: "users"
                    accentColor: "#06b6d4"
                    badgeText: Strings.badgeFreeFloat
                }

                // Kart 3: Hakim Ortak & Blok Pay
                RatioCard {
                    title: Strings.labelControllingShareholder
                    value: {
                        if (!root.ctrl) return "—";
                        var ff = root.ctrl.freeFloatPct || 0.0;
                        if (ff <= 0.0 || ff >= 1.0) return "—";
                        return "%" + ((1.0 - ff) * 100.0).toFixed(2);
                    }
                    subtitle: Strings.labelControllingShareholderDesc
                    iconName: "target"
                    accentColor: "#8b5cf6"
                    badgeText: Strings.badgeBlockShare
                }

                // Kart 4: Toplam Bildirim & Senkronizasyon
                ModernCard {
                    Layout.fillWidth: true
                    implicitHeight: 88

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Rectangle {
                                width: 22
                                height: 22
                                radius: Theme.radiusSm
                                color: Qt.rgba(245/255, 158/255, 11/255, 0.15)
                                Layout.alignment: Qt.AlignVCenter

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "history"
                                    size: 11
                                    color: "#f59e0b"
                                }
                            }

                            Text {
                                text: Strings.labelTotalFilings
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Medium
                                color: Theme.textSecondary
                                Layout.fillWidth: true
                            }

                            ModernButton {
                                text: Strings.btnSyncKap
                                iconName: "refresh"
                                variant: "primary"
                                onClicked: {
                                    if (root.ctrl) root.ctrl.refreshShareholdersHistory()
                                }
                            }
                        }

                        Text {
                            text: Strings.kapSnapshotCountTmpl.arg(root.ctrl ? root.ctrl.kapSnapshotCount : 0)
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }

                        Text {
                            text: Strings.labelLastKapUpdate + ": " + (root.ctrl ? root.ctrl.lastKapFilingDate : "—")
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // 2. ORTA BÖLÜM: 2 SÜTUNLU FINTECH DİSCLOSURE MERKEZİ
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

                // Sol: Ortaklık Dağılımı Donut Kartı (Genişletilmiş fullView modu)
                ShareholderPieCard {
                    fullView: true
                    Layout.fillWidth: true
                    Layout.preferredWidth: 440
                    Layout.minimumWidth: 360
                }

                // Sağ: Kronolojik Pay Değişim Zaman Çizelgesi (Filtre ve Arama destekli)
                FintechShareholderTimeline {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 560
                    Layout.minimumWidth: 420
                }
            }
        }
    }
}


