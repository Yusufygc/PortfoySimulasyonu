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

        // 1. Üst Bar: 4 Grafik Sekmesi & Hızlı Dönem Butonları
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            // 4 Grafik Sekmesi (Segment)
            Row {
                spacing: Theme.spaceXs

                Repeater {
                    model: [
                        { idx: 0, text: Strings.compareTabCumulative, icon: "linechart" },
                        { idx: 1, text: Strings.compareTabDrawdown, icon: "trendingdown" },
                        { idx: 2, text: Strings.compareTabPeriodic, icon: "barchart" },
                        { idx: 3, text: Strings.compareTabScatter, icon: "target" }
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

            Item { Layout.fillWidth: true }

            // Hızlı Dönem Butonları
            Row {
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
        RowLayout {
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

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
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
                    text: "Karşılaştırma hesaplanıyor..."
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
