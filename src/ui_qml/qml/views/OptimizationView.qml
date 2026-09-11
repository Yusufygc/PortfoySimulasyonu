import QtQuick
import QtQuick.Controls
import PortfoyCharts 1.0

// OptimizationView (bkz. plan §7.3 madde 5, d5) — Markowitz optimizasyonu:
// kaynak seçimi (Dashboard/Model Portföyü) + risk profili slider'ı (geçici
// önizleme, kayıtlı anket profilini DEĞİŞTİRMEZ) + Verimli Sınır'ın 3 noktası
// (Mevcut/Min. Risk/Maks. Sharpe, `ScatterChartItem` yeniden kullanılıyor) +
// önerilen değişiklik (rebalancing) tablosu. Veri: context property
// `optimizationController` (bkz. src/ui_qml/controllers/optimization_controller.py).
//
// Not: Layout `headerColumn` + `contentArea` (Flickable, anchors ile kalan
// alanı dolduran) deseni — Stock360View'daki NaN-yükseklik hatasından ders
// alınarak (bkz. TRANSFORMATION_PLAN §9).
Item {
    id: root
    anchors.fill: parent

    readonly property color colorAccent: "#3B82F6"
    readonly property color colorProfit: "#10B981"
    readonly property color colorLoss: "#EF4444"
    readonly property color colorMuted: "#9CA3AF"

    function pctColor(value) { return value >= 0 ? colorProfit : colorLoss }
    function fmtPct(value) { return (value >= 0 ? "+" : "") + value.toFixed(2) + "%" }

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 10

        Text { text: "Optimizasyon & Risk"; color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }

        Row {
            spacing: 12

            Text { text: "Kaynak:"; color: root.colorMuted; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12 }

            ComboBox {
                id: sourceCombo
                width: 220
                model: optimizationController.sourceLabels
                onActivated: optimizationController.selectSourceByIndex(currentIndex)
            }

            Button {
                text: "Yeniden Hesapla"
                onClicked: optimizationController.runOptimization()
            }
        }

        Column {
            width: 340
            spacing: 4

            Text {
                text: "Risk Profili: " + optimizationController.activeRiskLabelDisplay
                    + (optimizationController.isManualOverride ? " (geçici önizleme)"
                        : (optimizationController.usedDefaultProfile ? " (varsayılan)" : " (kayıtlı profil)"))
                color: root.colorMuted
                font.pixelSize: 12
            }

            Slider {
                id: riskSlider
                width: parent.width
                from: 0
                to: 4
                stepSize: 1
                value: optimizationController.sliderIndex
                onMoved: optimizationController.setSliderIndex(Math.round(value))
            }

            Row {
                width: riskSlider.width
                Repeater {
                    model: optimizationController.riskLabelDisplayNames
                    delegate: Text {
                        width: riskSlider.width / 5
                        text: modelData
                        color: root.colorMuted
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
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

            Text {
                visible: !optimizationController.hasResult
                width: parent.width
                text: optimizationController.errorMessage !== "" ? optimizationController.errorMessage : "Optimizasyon çalıştırılıyor..."
                color: root.colorLoss
                wrapMode: Text.WordWrap
                font.pixelSize: 12
            }

            // ---- Metrik Kartları: Mevcut / Minimum Risk / Maksimum Sharpe ----
            Row {
                visible: optimizationController.hasResult
                width: parent.width
                spacing: 16
                height: 110

                Rectangle {
                    width: (parent.width - 32) / 3
                    height: parent.height
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1

                    Column {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 14
                        spacing: 4

                        Text { text: "Mevcut Portföy"; color: root.colorMuted; font.pixelSize: 12 }
                        Text { text: "Getiri: " + root.fmtPct(optimizationController.currentReturnPct); color: "#E5E7EB"; font.pixelSize: 13 }
                        Text { text: "Risk: %" + optimizationController.currentVolatilityPct.toFixed(2); color: "#E5E7EB"; font.pixelSize: 13 }
                        Text { text: "Sharpe: " + optimizationController.currentSharpe.toFixed(3); color: "#E5E7EB"; font.pixelSize: 13 }
                    }
                }

                Rectangle {
                    width: (parent.width - 32) / 3
                    height: parent.height
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1

                    Column {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 14
                        spacing: 4

                        Text { text: "Minimum Risk Noktası"; color: root.colorMuted; font.pixelSize: 12 }
                        Text { text: "Getiri: " + root.fmtPct(optimizationController.minVolatilityReturnPct); color: "#E5E7EB"; font.pixelSize: 13 }
                        Text { text: "Risk: %" + optimizationController.minVolatilityVolatilityPct.toFixed(2); color: "#E5E7EB"; font.pixelSize: 13 }
                        Text { text: "Sharpe: " + optimizationController.minVolatilitySharpe.toFixed(3); color: "#E5E7EB"; font.pixelSize: 13 }
                    }
                }

                Rectangle {
                    width: (parent.width - 32) / 3
                    height: parent.height
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1

                    Column {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 14
                        spacing: 4

                        Text { text: "Maks. Sharpe (Önerilen)"; color: root.colorMuted; font.pixelSize: 12 }
                        Text { text: "Getiri: " + root.fmtPct(optimizationController.optimizedReturnPct); color: root.colorProfit; font.pixelSize: 13 }
                        Text { text: "Risk: %" + optimizationController.optimizedVolatilityPct.toFixed(2); color: "#E5E7EB"; font.pixelSize: 13 }
                        Text { text: "Sharpe: " + optimizationController.optimizedSharpe.toFixed(3); color: root.colorProfit; font.pixelSize: 13 }
                    }
                }
            }

            // ---- Verimli Sınır (Efficient Frontier) — 3 nokta ----
            Rectangle {
                visible: optimizationController.hasResult
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
                        id: frontierScatter
                        width: parent.width * 0.62
                        height: parent.height
                        valuesX: optimizationController.frontierVolatilityPct
                        valuesY: optimizationController.frontierReturnPct
                    }

                    Column {
                        width: parent.width - frontierScatter.width - 14
                        spacing: 6

                        Text { text: "Verimli Sınır (Efficient Frontier)"; color: root.colorMuted; font.pixelSize: 12 }
                        Text { text: "X: Risk (Yıllık Oynaklık %), Y: Beklenen Yıllık Getiri %"; color: root.colorMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; width: parent.width }

                        Repeater {
                            model: optimizationController.frontierLabels.length
                            delegate: Text {
                                text: optimizationController.frontierLabels[index] + ": %" + optimizationController.frontierVolatilityPct[index].toFixed(1) + " risk / %" + optimizationController.frontierReturnPct[index].toFixed(1) + " getiri"
                                color: "#E5E7EB"
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }

            // ---- Önerilen Değişiklik Tablosu (Rebalancing) ----
            Rectangle {
                visible: optimizationController.hasResult
                width: parent.width
                height: 60 + optimizationController.suggestionTickers.length * 30
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text { text: "Önerilen Değişiklik (Rebalancing)"; color: root.colorMuted; font.pixelSize: 12 }

                    Repeater {
                        model: optimizationController.suggestionTickers.length
                        delegate: Row {
                            spacing: 20

                            Text { width: 90; text: optimizationController.suggestionTickers[index]; color: "#E5E7EB"; font.bold: true; font.pixelSize: 12 }
                            Text { width: 110; text: "Mevcut: %" + optimizationController.suggestionCurrentWeightPct[index].toFixed(1); color: root.colorMuted; font.pixelSize: 12 }
                            Text { width: 110; text: "Hedef: %" + optimizationController.suggestionOptimalWeightPct[index].toFixed(1); color: "#E5E7EB"; font.pixelSize: 12 }
                            Text { width: 90; text: root.fmtPct(optimizationController.suggestionChangePct[index]); color: root.pctColor(optimizationController.suggestionChangePct[index]); font.pixelSize: 12 }

                            Rectangle {
                                width: 60
                                height: 20
                                radius: 6
                                color: optimizationController.suggestionActions[index] === "EKLE" ? root.colorProfit
                                    : (optimizationController.suggestionActions[index] === "AZALT" ? root.colorLoss : "#26354A")

                                Text {
                                    anchors.centerIn: parent
                                    text: optimizationController.suggestionActions[index]
                                    color: "#0B0F19"
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
