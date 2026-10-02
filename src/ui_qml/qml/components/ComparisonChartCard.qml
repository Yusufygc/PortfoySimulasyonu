import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"

Rectangle {
    id: root

    color: Theme.bgCard
    radius: Theme.radiusMd
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // 1. Üst Bar: Grafik Sekmeleri & Hızlı Dönem Butonları (sığmazsa dönem butonları alta sarar)
        Flow {
            id: topFlow
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            // 5 Grafik Sekmesi (Segment)
            Row {
                id: tabsRow
                spacing: Theme.spaceXs

                Repeater {
                    model: [
                        { idx: 0, text: Strings.compareTabCumulative, icon: "linechart" },
                        { idx: 1, text: Strings.compareTabDrawdown, icon: "trendingdown" },
                        { idx: 2, text: Strings.compareTabPeriodic, icon: "barchart" },
                        { idx: 3, text: Strings.compareTabScatter, icon: "target" },
                        { idx: 4, text: Strings.compareTabTreemap, icon: "layers" }
                    ]

                    Rectangle {
                        width: tabBtnRow.width + 16
                        height: 30
                        radius: Theme.radiusSm
                        color: comparisonController.activeChartTab === modelData.idx ? Theme.accent : (tabMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                        border.color: comparisonController.activeChartTab === modelData.idx ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            id: tabBtnRow
                            anchors.centerIn: parent
                            spacing: 4

                            ModernIcon {
                                name: modelData.icon
                                color: comparisonController.activeChartTab === modelData.idx ? Theme.textInverse : Theme.textSecondary
                                size: 12
                            }

                            Text {
                                text: modelData.text
                                color: comparisonController.activeChartTab === modelData.idx ? Theme.textInverse : Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: comparisonController.activeChartTab === modelData.idx ? Font.DemiBold : Font.Normal
                            }
                        }

                        MouseArea {
                            id: tabMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: comparisonController.setActiveChartTab(modelData.idx)
                        }
                    }
                }
            }

            // Sığıyorsa dönem butonlarını sağa yaslar, sığmıyorsa 0 genişlikte kalır
            Item {
                height: 1
                width: Math.max(0, topFlow.width - tabsRow.width - periodsRow.width - topFlow.spacing * 2)
            }

            // Hızlı Dönem Butonları
            Row {
                id: periodsRow
                spacing: Theme.spaceXs

                Repeater {
                    model: ["1A", "3A", "6A", "1Y", "YBB", "Tümü"]

                    Rectangle {
                        width: 42
                        height: 30
                        radius: Theme.radiusSm
                        color: comparisonController.periodLabel === modelData ? Theme.accent : (btnMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                        border.color: comparisonController.periodLabel === modelData ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: comparisonController.periodLabel === modelData ? Theme.textInverse : Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: comparisonController.periodLabel === modelData ? Font.Bold : Font.Normal
                        }

                        MouseArea {
                            id: btnMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: comparisonController.setPeriod(modelData)
                        }
                    }
                }
            }
        }

        // 2. İkinci Bar: Mod Seçici (Normalize, Normal, Rasyo) — Sadece Getiri Grafiğinde Görünür
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceSm
            visible: comparisonController.activeChartTab === 0

            Text {
                text: Strings.compareModeTitle + ":"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }

            // 3 Mod Butonları
            Row {
                spacing: Theme.spaceXs

                Repeater {
                    model: [
                        { key: "NORMALIZED", text: Strings.compareModeNormalized },
                        { key: "NORMAL", text: Strings.compareModeNormal },
                        { key: "RATIO", text: Strings.compareModeRatio }
                    ]

                    Rectangle {
                        width: modeText.width + 16
                        height: 26
                        radius: Theme.radiusXs
                        color: comparisonController.comparisonMode === modelData.key ? Theme.accentSoft : (mMouse.containsMouse ? Theme.bgCardHover : "transparent")
                        border.color: comparisonController.comparisonMode === modelData.key ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        Text {
                            id: modeText
                            anchors.centerIn: parent
                            text: modelData.text
                            color: comparisonController.comparisonMode === modelData.key ? Theme.accent : Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: comparisonController.comparisonMode === modelData.key ? Font.DemiBold : Font.Normal
                        }

                        MouseArea {
                            id: mMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: comparisonController.setComparisonMode(modelData.key)
                        }
                    }
                }
            }

            // Rasyo Seçicileri (Pay / Payda)
            RowLayout {
                spacing: Theme.spaceSm
                visible: comparisonController.comparisonMode === "RATIO"

                Text {
                    text: Strings.compareRatioNumLabel
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }

                ComboBox {
                    id: numCombo
                    Layout.preferredWidth: 130
                    Layout.preferredHeight: 26
                    model: comparisonController.metricsList
                    textRole: "label"
                    currentIndex: 0

                    contentItem: Text {
                        leftPadding: 6
                        text: numCombo.displayText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    onActivated: function(idx) {
                        var opt = comparisonController.metricsList[idx]
                        if (opt) comparisonController.setRatioAssets(opt.code, comparisonController.ratioDenominator)
                    }
                }

                Text {
                    text: "/"
                    color: Theme.textMuted
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                }

                Text {
                    text: Strings.compareRatioDenLabel
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                }

                ComboBox {
                    id: denCombo
                    Layout.preferredWidth: 130
                    Layout.preferredHeight: 26
                    model: comparisonController.metricsList
                    textRole: "label"
                    currentIndex: Math.min(1, comparisonController.metricsList.length - 1)

                    contentItem: Text {
                        leftPadding: 6
                        text: denCombo.displayText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    onActivated: function(idx) {
                        var opt = comparisonController.metricsList[idx]
                        if (opt) comparisonController.setRatioAssets(comparisonController.ratioNumerator, opt.code)
                    }
                }
            }

            Item { Layout.fillWidth: true }
        }

        // Treemap Mod Seçici (Ana Portföy Hisseleri vs Seçilen Varlıklar) — Sadece Treemap Sekmesinde Görünür
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm
            visible: comparisonController.activeChartTab === 4

            Text {
                text: Strings.compareTreemapModeTitle + ":"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
            }

            // 2 Mod Butonu: Ana Portföy Hisseleri / Seçilen Varlıklar
            Row {
                spacing: Theme.spaceXs

                Repeater {
                    model: [
                        { key: "HOLDINGS", text: Strings.compareTreemapModeHoldings, icon: "piechart" },
                        { key: "ASSETS", text: Strings.compareTreemapModeCompare, icon: "layers" }
                    ]

                    Rectangle {
                        width: tmModeRow.width + 16
                        height: 26
                        radius: Theme.radiusXs
                        color: comparisonController.treemapMode === modelData.key ? Theme.accentSoft : (tmMouse.containsMouse ? Theme.bgCardHover : "transparent")
                        border.color: comparisonController.treemapMode === modelData.key ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            id: tmModeRow
                            anchors.centerIn: parent
                            spacing: 4

                            ModernIcon {
                                name: modelData.icon
                                color: comparisonController.treemapMode === modelData.key ? Theme.accent : Theme.textSecondary
                                size: 12
                            }

                            Text {
                                text: modelData.text
                                color: comparisonController.treemapMode === modelData.key ? Theme.accent : Theme.textSecondary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: comparisonController.treemapMode === modelData.key ? Font.DemiBold : Font.Normal
                            }
                        }

                        MouseArea {
                            id: tmMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: comparisonController.setTreemapMode(modelData.key)
                        }
                    }
                }
            }

            // Portföy Seçici Dropdown (Sadece Portföy Hisseleri modundayken görünür)
            RowLayout {
                spacing: Theme.spaceXs
                visible: comparisonController.treemapMode === "HOLDINGS" && comparisonController.treemapPortfolioOptions.length > 0

                Rectangle {
                    width: 1
                    height: 18
                    color: Theme.borderSubtle
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                }

                Text {
                    text: Strings.compareTreemapPortfolioSelect
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                }

                ComboBox {
                    id: portfolioCombo
                    Layout.preferredWidth: 155
                    Layout.preferredHeight: 26
                    model: comparisonController.treemapPortfolioOptions
                    textRole: "label"

                    currentIndex: {
                        for (var i = 0; i < comparisonController.treemapPortfolioOptions.length; i++) {
                            if (comparisonController.treemapPortfolioOptions[i].code === comparisonController.treemapPortfolio) {
                                return i
                            }
                        }
                        return 0
                    }

                    background: Rectangle {
                        color: Theme.bgSecondary
                        radius: Theme.radiusXs
                        border.color: portfolioCombo.hovered ? Theme.accent : Theme.borderSubtle
                        border.width: 1
                    }

                    contentItem: Text {
                        leftPadding: 8
                        rightPadding: 20
                        text: portfolioCombo.displayText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    indicator: ModernIcon {
                        anchors.right: parent.right
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        name: "chevrondown"
                        size: 10
                        color: Theme.textMuted
                    }

                    popup: Popup {
                        y: portfolioCombo.height + 2
                        width: Math.max(portfolioCombo.width, 165)
                        implicitHeight: Math.min(220, contentItem.implicitHeight + 8)
                        padding: 4

                        contentItem: ListView {
                            clip: true
                            implicitHeight: contentHeight
                            model: portfolioCombo.popup.visible ? portfolioCombo.delegateModel : null
                            currentIndex: portfolioCombo.highlightedIndex

                            ScrollIndicator.vertical: ScrollIndicator {}
                        }

                        background: Rectangle {
                            color: Theme.bgCard
                            border.color: Theme.borderCard
                            border.width: 1
                            radius: Theme.radiusSm
                        }
                    }

                    delegate: ItemDelegate {
                        width: portfolioCombo.width
                        height: 28
                        highlighted: portfolioCombo.highlightedIndex === index

                        contentItem: Text {
                            text: modelData.label
                            color: highlighted ? Theme.accent : Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        background: Rectangle {
                            color: highlighted ? Theme.accentSoft : (hovered ? Theme.bgCardHover : "transparent")
                            radius: Theme.radiusXs
                        }
                    }

                    onActivated: function(idx) {
                        var opt = comparisonController.treemapPortfolioOptions[idx]
                        if (opt && opt.code) {
                            comparisonController.setTreemapPortfolio(opt.code)
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // Grafik açıklaması (Nedir / Nasıl Yorumlanır); ana grafikte seçili moda göre değişir
        ChartInfoCard {
            readonly property int tab: comparisonController.activeChartTab
            readonly property string mode: comparisonController.comparisonMode
            title: [Strings.compareInfoCumulativeTitle, Strings.compareInfoDrawdownTitle, Strings.compareInfoPeriodicTitle,
                    Strings.compareInfoScatterTitle, Strings.compareInfoTreemapTitle][tab] || ""
            what: tab === 0
                  ? (mode === "RATIO" ? Strings.compareInfoCumulativeRatioWhat
                     : mode === "NORMALIZED" ? Strings.compareInfoCumulativeNormalizeWhat : Strings.compareInfoCumulativeWhat)
                  : ([Strings.compareInfoDrawdownWhat, Strings.compareInfoPeriodicWhat,
                      Strings.compareInfoScatterWhat, Strings.compareInfoTreemapWhat][tab - 1] || "")
            how: tab === 0
                 ? (mode === "RATIO" ? Strings.compareInfoCumulativeRatioHow
                    : mode === "NORMALIZED" ? Strings.compareInfoCumulativeNormalizeHow : Strings.compareInfoCumulativeHow)
                 : ([Strings.compareInfoDrawdownHow, Strings.compareInfoPeriodicHow,
                     Strings.compareInfoScatterHow, Strings.compareInfoTreemapHow][tab - 1] || "")
        }

        // 3. Grafik veya Boş Durum
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // WebEngineView Grafik
            WebEngineView {
                id: chartWebView
                anchors.fill: parent
                backgroundColor: Theme.bgCard
                visible: comparisonController.chartHtml !== "" && !comparisonController.isLoading

                settings.javascriptEnabled: true
                settings.localContentCanAccessRemoteUrls: true

                Connections {
                    target: comparisonController
                    function onChartHtmlChanged() {
                        if (comparisonController.chartHtml !== "") {
                            chartWebView.loadHtml(comparisonController.chartHtml)
                        }
                    }
                }

                Component.onCompleted: {
                    if (comparisonController.chartHtml !== "") {
                        chartWebView.loadHtml(comparisonController.chartHtml)
                    }
                }
            }

            // Yükleniyor Durumu
            ColumnLayout {
                anchors.centerIn: parent
                visible: comparisonController.isLoading
                spacing: Theme.spaceSm

                BusyIndicator {
                    Layout.alignment: Qt.AlignHCenter
                    running: comparisonController.isLoading
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.comparisonCalculating
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            // Boş Durum
            ColumnLayout {
                anchors.centerIn: parent
                visible: comparisonController.chartHtml === "" && !comparisonController.isLoading
                spacing: Theme.spaceSm

                ModernIcon {
                    Layout.alignment: Qt.AlignHCenter
                    name: "compare"
                    color: Theme.textMuted
                    size: 40
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.compareEmptyTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.compareEmptySubtitle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }
    }
}
