import QtQuick
import QtQuick.Controls
import PortfoyCharts 1.0

// AnalyticsView (bkz. plan §7.3 madde 4, d4) — Karşılaştırma Laboratuvarı'nın
// 5 grafik paneli (kümülatif performans/özet tablo/drawdown/dönemsel getiri/
// risk-getiri saçılımı) + gelişmiş risk/performans paneli + aylık getiri ısı
// haritası + treemap getiri katkı haritası (6. panel, `TreemapChartItem` —
// squarified algoritma `treemap_mapper.py`'de saf Python, plan §7.4'te ayrı
// bir alt-görev olarak not edilmişti). Veri: context property
// `analyticsController` (bkz. src/ui_qml/controllers/analytics_controller.py).
//
// Not: Layout `headerColumn` + `contentArea` (Flickable, anchors ile kalan
// alanı dolduran) deseni — Stock360View'daki NaN-yükseklik hatasından ders
// alınarak (bkz. TRANSFORMATION_PLAN §9).
Item {
    id: root
    anchors.fill: parent

    readonly property color colorAccent: "#3B82F6"
    readonly property color colorAccent2: "#F59E0B"
    readonly property color colorProfit: "#10B981"
    readonly property color colorLoss: "#EF4444"
    readonly property color colorMuted: "#9CA3AF"
    readonly property color colorNoData: "#26354A"
    readonly property real missingSentinel: -9999.0

    function pctColor(value) { return value >= 0 ? colorProfit : colorLoss }
    function fmtPct(value) { return (value >= 0 ? "+" : "") + value.toFixed(2) + "%" }
    function heatColor(value) {
        if (value <= root.missingSentinel + 1)
            return root.colorNoData
        var t = Math.max(-1, Math.min(1, value / 10.0))  // ±%10 doygunluk sınırı
        return t >= 0 ? Qt.rgba(0.06, 0.7 * t + 0.15, 0.35, 1.0) : Qt.rgba(0.7 * -t + 0.15, 0.08, 0.1, 1.0)
    }

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 4

        Text { text: "Analiz & Kıyaslama Laboratuvarı"; color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }
        Text { text: "Portföy vs " + (analyticsController.benchmarkLabel !== "" ? analyticsController.benchmarkLabel : "-"); color: root.colorMuted; font.pixelSize: 12 }
    }

    Flickable {
        id: contentArea
        objectName: "contentArea"
        anchors.top: headerColumn.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.topMargin: 14
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        anchors.bottomMargin: 20
        contentHeight: panelsColumn.height
        clip: true

        Column {
            id: panelsColumn
            width: contentArea.width
            spacing: 16

            // ---- 1. Kümülatif Getiri & Performans (Baz 100) ----
            Rectangle {
                width: parent.width
                height: 220
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Text { text: "Kümülatif Getiri & Performans (Baz 100)"; color: root.colorMuted; font.pixelSize: 12 }

                    LineChartItem {
                        width: parent.width
                        height: parent.height - 60
                        values: analyticsController.portfolioPerformanceValues
                        values2: analyticsController.benchmarkPerformanceValues
                        lineColor: root.colorAccent
                        lineColor2: root.colorAccent2
                    }

                    Row {
                        spacing: 16
                        Row { spacing: 6; Rectangle { width: 10; height: 10; radius: 5; color: root.colorAccent } Text { text: "Portföy"; color: root.colorMuted; font.pixelSize: 11 } }
                        Row { spacing: 6; Rectangle { width: 10; height: 10; radius: 5; color: root.colorAccent2 } Text { text: analyticsController.benchmarkLabel; color: root.colorMuted; font.pixelSize: 11 } }
                    }
                }
            }

            // ---- 2. Dönem Sonu Getiri Özeti Tablosu ----
            Rectangle {
                width: parent.width
                height: 60 + analyticsController.summaryLabels.length * 26
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text { text: "Dönem Sonu Getiri Özeti"; color: root.colorMuted; font.pixelSize: 12 }

                    Repeater {
                        model: analyticsController.summaryLabels.length
                        delegate: Row {
                            spacing: 20
                            Text { width: 140; text: analyticsController.summaryLabels[index]; color: "#E5E7EB"; font.pixelSize: 12 }
                            Text { width: 90; text: "Portföy: " + root.fmtPct(analyticsController.summaryPortfolioReturnPct[index]); color: root.pctColor(analyticsController.summaryPortfolioReturnPct[index]); font.pixelSize: 12 }
                            Text { width: 110; text: "Benchmark: " + root.fmtPct(analyticsController.summaryBenchmarkReturnPct[index]); color: root.colorMuted; font.pixelSize: 12 }
                            Text { width: 90; text: "Fark: " + root.fmtPct(analyticsController.summaryRelativeGapPct[index]); color: root.pctColor(analyticsController.summaryRelativeGapPct[index]); font.pixelSize: 12 }
                        }
                    }

                    Text {
                        visible: analyticsController.summaryLabels.length === 0
                        text: "Kıyaslama verisi yok."
                        color: root.colorMuted
                        font.pixelSize: 11
                    }
                }
            }

            // ---- 3. Maksimum Drawdown ----
            Rectangle {
                width: parent.width
                height: 180
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Text { text: "Maksimum Drawdown (Değer Kaybı & Underwater)"; color: root.colorMuted; font.pixelSize: 12 }

                    LineChartItem {
                        width: parent.width
                        height: parent.height - 30
                        values: analyticsController.drawdownValues
                        lineColor: root.colorLoss
                    }
                }
            }

            // ---- 4. Dönemsel Getiri Karşılaştırma (Bar) ----
            Rectangle {
                width: parent.width
                height: 220
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Text { text: "Dönemsel Getiri Karşılaştırma (Aylık)"; color: root.colorMuted; font.pixelSize: 12 }

                    BarChartItem {
                        id: periodicReturnsBar
                        width: parent.width
                        height: parent.height - 60
                        values: analyticsController.periodicReturnValues
                    }

                    Flickable {
                        width: parent.width
                        height: 20
                        contentWidth: periodicLabelsRow.width
                        clip: true

                        Row {
                            id: periodicLabelsRow
                            spacing: (periodicReturnsBar.width / Math.max(1, analyticsController.periodicReturnLabels.length)) - 40
                            Repeater {
                                model: analyticsController.periodicReturnLabels
                                delegate: Text { width: 40; text: modelData; color: root.colorMuted; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                    }
                }
            }

            // ---- 5. Risk / Getiri Dağılımı (Scatter) ----
            Rectangle {
                width: parent.width
                height: 260
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Row {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14

                    ScatterChartItem {
                        id: riskReturnScatter
                        width: parent.width * 0.62
                        height: parent.height
                        valuesX: analyticsController.scatterVolatilityPct
                        valuesY: analyticsController.scatterReturnPct
                    }

                    Column {
                        width: parent.width - riskReturnScatter.width - 14
                        spacing: 6

                        Text { text: "Risk / Getiri Dağılımı"; color: root.colorMuted; font.pixelSize: 12 }
                        Text { text: "X: Yıllık Oynaklık %, Y: Toplam Getiri %"; color: root.colorMuted; font.pixelSize: 10 }

                        Repeater {
                            model: analyticsController.scatterLabels.length
                            delegate: Text {
                                text: analyticsController.scatterLabels[index] + ": " + analyticsController.scatterVolatilityPct[index].toFixed(1) + "% / " + analyticsController.scatterReturnPct[index].toFixed(1) + "%"
                                color: "#E5E7EB"
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }

            // ---- 6. Treemap Getiri Katkı Haritası ----
            Rectangle {
                width: parent.width
                height: 260
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Text { text: "Treemap Getiri Katkı Haritası"; color: root.colorMuted; font.pixelSize: 12 }

                    TreemapChartItem {
                        width: parent.width
                        height: parent.height - 30
                        items: analyticsController.treemapItems
                    }
                }
            }

            // ---- 7. Gelişmiş Risk/Performans Paneli ----
            Rectangle {
                width: parent.width
                height: 140
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Text { text: "Gelişmiş Risk / Performans Paneli"; color: root.colorMuted; font.pixelSize: 12 }

                    Grid {
                        columns: 5
                        columnSpacing: 24
                        rowSpacing: 10

                        Column { Text { text: "Sharpe"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.sharpeRatio.toFixed(2); color: "#E5E7EB"; font.pixelSize: 14 } }
                        Column { Text { text: "Sortino"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.sortinoRatio.toFixed(2); color: "#E5E7EB"; font.pixelSize: 14 } }
                        Column { Text { text: "Calmar"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.calmarRatio.toFixed(2); color: "#E5E7EB"; font.pixelSize: 14 } }
                        Column { Text { text: "Omega"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.omegaRatio.toFixed(2); color: "#E5E7EB"; font.pixelSize: 14 } }
                        Column { Text { text: "Beta"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.beta.toFixed(2); color: "#E5E7EB"; font.pixelSize: 14 } }

                        Column { Text { text: "Alfa"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.alpha.toFixed(2); color: root.pctColor(analyticsController.alpha); font.pixelSize: 14 } }
                        Column { Text { text: "R²"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.rSquared.toFixed(2); color: "#E5E7EB"; font.pixelSize: 14 } }
                        Column { Text { text: "Tracking Error %"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.trackingErrorPct.toFixed(2); color: "#E5E7EB"; font.pixelSize: 14 } }
                        Column { Text { text: "VaR %95"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.valueAtRisk95Pct.toFixed(2); color: root.colorLoss; font.pixelSize: 14 } }
                        Column { Text { text: "CVaR %95"; color: root.colorMuted; font.pixelSize: 10 } Text { text: analyticsController.conditionalVar95Pct.toFixed(2); color: root.colorLoss; font.pixelSize: 14 } }
                    }
                }
            }

            // ---- Aylık Getiri Isı Haritası ----
            Rectangle {
                width: parent.width
                height: 60 + analyticsController.monthlyHeatmapYears.length * 24
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text { text: "Aylık Getiri Isı Haritası"; color: root.colorMuted; font.pixelSize: 12 }

                    Repeater {
                        model: analyticsController.monthlyHeatmapYears.length
                        delegate: Row {
                            property int yearIndex: index
                            spacing: 2

                            Text {
                                width: 40
                                text: analyticsController.monthlyHeatmapYears[yearIndex].toString()
                                color: root.colorMuted
                                font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Repeater {
                                model: 12
                                delegate: Rectangle {
                                    property real cellValue: analyticsController.monthlyHeatmapRows[yearIndex][index]
                                    width: 28
                                    height: 20
                                    color: root.heatColor(cellValue)
                                    Text {
                                        anchors.centerIn: parent
                                        visible: cellValue > root.missingSentinel + 1
                                        text: cellValue.toFixed(0)
                                        color: "#E5E7EB"
                                        font.pixelSize: 8
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
