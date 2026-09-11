import QtQuick
import QtQuick.Controls
import PortfoyCharts 1.0

// SimulationView (bkz. plan §7.3 madde 6, d5) — DCA (Düzenli Katkı) backtest
// formu: ticker girişi + aylık katkı + tarih aralığı butonları + portföy
// değeri grafiği + özet + hisse bazlı lot dökümü. Veri: context property
// `simulationController` (bkz. src/ui_qml/controllers/simulation_controller.py).
//
// Not (plan'dan dürüst sapma): "Periyodik yeniden dengeleme (Rebalance)
// karşılaştırması" burada YOK — backend (`DCABacktestService`) bunu v1
// kapsamı dışında bırakmıştı (bkz. plan §9.12), icat edilmedi.
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
    function fmtMoney(value) { return value.toLocaleString(Qt.locale("tr_TR"), 'f', 2) }

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 10

        Text { text: "Strateji Simülatörü (DCA Backtest)"; color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }
        Text {
            text: "\"Geçmişte her ay X TL hisse alsaydım\" senaryosu — hisseler eşit ağırlıkla dağıtılır."
            color: root.colorMuted
            font.pixelSize: 11
        }

        Row {
            spacing: 12

            TextField {
                id: tickersField
                width: 260
                placeholderText: "Ticker'lar (örn. AKBNK, FROTO)"
                text: simulationController.tickersText
                onTextChanged: simulationController.setTickersText(text)
            }

            TextField {
                id: contributionField
                width: 140
                placeholderText: "Aylık Katkı (TL)"
                text: simulationController.monthlyContribution.toString()
                validator: DoubleValidator { bottom: 0 }
                onTextChanged: {
                    var value = parseFloat(text)
                    if (!isNaN(value)) simulationController.setMonthlyContribution(value)
                }
            }

            Button {
                text: "Çalıştır"
                onClicked: simulationController.runSimulation()
            }
        }

        Row {
            spacing: 8
            Repeater {
                model: simulationController.rangeKeys
                delegate: Button {
                    text: simulationController.rangeLabels[index]
                    checkable: true
                    checked: simulationController.selectedRangeKey === modelData
                    onClicked: simulationController.setSelectedRangeKey(modelData)
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
                visible: !simulationController.hasResult
                width: parent.width
                text: simulationController.errorMessage !== "" ? simulationController.errorMessage : "Ticker'ları girip \"Çalıştır\"a basın."
                color: simulationController.errorMessage !== "" ? root.colorLoss : root.colorMuted
                wrapMode: Text.WordWrap
                font.pixelSize: 12
            }

            // ---- Özet Kartları ----
            Row {
                visible: simulationController.hasResult
                width: parent.width
                spacing: 16
                height: 100

                Rectangle {
                    width: (parent.width - 48) / 4
                    height: parent.height
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1
                    Column {
                        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 14; spacing: 4
                        Text { text: "Toplam Yatırım"; color: root.colorMuted; font.pixelSize: 11 }
                        Text { text: root.fmtMoney(simulationController.totalInvested) + " ₺"; color: "#E5E7EB"; font.pixelSize: 16; font.bold: true }
                    }
                }

                Rectangle {
                    width: (parent.width - 48) / 4
                    height: parent.height
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1
                    Column {
                        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 14; spacing: 4
                        Text { text: "Güncel Değer"; color: root.colorMuted; font.pixelSize: 11 }
                        Text { text: root.fmtMoney(simulationController.finalValue) + " ₺"; color: "#E5E7EB"; font.pixelSize: 16; font.bold: true }
                    }
                }

                Rectangle {
                    width: (parent.width - 48) / 4
                    height: parent.height
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1
                    Column {
                        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 14; spacing: 4
                        Text { text: "Toplam Getiri"; color: root.colorMuted; font.pixelSize: 11 }
                        Text { text: root.fmtPct(simulationController.totalReturnPct); color: root.pctColor(simulationController.totalReturnPct); font.pixelSize: 16; font.bold: true }
                    }
                }

                Rectangle {
                    width: (parent.width - 48) / 4
                    height: parent.height
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1
                    Column {
                        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 14; spacing: 4
                        Text { text: "Katkı Sayısı"; color: root.colorMuted; font.pixelSize: 11 }
                        Text { text: simulationController.contributionCount.toString(); color: "#E5E7EB"; font.pixelSize: 16; font.bold: true }
                    }
                }
            }

            // ---- Portföy Değeri Grafiği ----
            Rectangle {
                visible: simulationController.hasResult
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

                    Text { text: "Portföy Değeri (Zaman İçinde)"; color: root.colorMuted; font.pixelSize: 12 }

                    LineChartItem {
                        width: parent.width
                        height: parent.height - 30
                        values: simulationController.portfolioValueSeries
                        lineColor: root.colorAccent
                    }
                }
            }

            // ---- Hisse Bazlı Lot Dökümü ----
            Rectangle {
                visible: simulationController.hasResult
                width: parent.width
                height: 60 + simulationController.breakdownTickers.length * 26
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text { text: "Hisse Bazlı Lot Dökümü"; color: root.colorMuted; font.pixelSize: 12 }

                    Repeater {
                        model: simulationController.breakdownTickers.length
                        delegate: Row {
                            spacing: 20
                            Text { width: 100; text: simulationController.breakdownTickers[index]; color: "#E5E7EB"; font.bold: true; font.pixelSize: 12 }
                            Text { text: "Lot: " + simulationController.breakdownShares[index].toFixed(4); color: root.colorMuted; font.pixelSize: 12 }
                        }
                    }
                }
            }
        }
    }
}
