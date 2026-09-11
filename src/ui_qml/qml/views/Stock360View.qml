import QtQuick
import QtQuick.Controls
import PortfoyCharts 1.0

// Stock360View (bkz. plan §7.3 madde 2) — arama kutusu + 3 sekme (Fiyat/TA,
// Bilanço/Rasyolar, Ortaklık Yapısı). Veri: context property `stock360Controller`
// (bkz. src/ui_qml/controllers/stock_360_controller.py).
//
// Not: Üst blok (arama + genel bakış + sekme çubuğu) `headerColumn` içinde
// otomatik yüksekliğiyle üstte, sekme içeriği `tabContent` anchor'larla kalan
// alanı doldurur — manuel yükseklik çıkarma aritmetiği (önceki sürümde
// `root.spacing` gibi var olmayan bir property'ye referans vererek NaN yüksekliğe
// yol açmıştı) yerine bu daha sağlam desen kullanıldı.
Item {
    id: root
    anchors.fill: parent

    readonly property color colorProfit: "#10B981"
    readonly property color colorLoss: "#EF4444"
    function pctColor(value) { return value >= 0 ? colorProfit : colorLoss }
    function fmt2(value) { return value.toFixed(2) }
    function fmtPct(value) { return (value >= 0 ? "+" : "") + value.toFixed(2) + "%" }

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 14

        // ---- Arama kutusu + Genel Bakış şeridi ----
        Row {
            width: parent.width
            spacing: 12

            Rectangle {
                width: 220
                height: 40
                radius: 8
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                TextField {
                    id: searchField
                    anchors.fill: parent
                    anchors.margins: 4
                    placeholderText: "Hisse Kodu (örn. THYAO)"
                    color: "#E5E7EB"
                    background: null
                    onAccepted: stock360Controller.loadTicker(text)
                }
            }

            Rectangle {
                visible: stock360Controller.ticker !== ""
                width: overviewRow.width + 24
                height: 40
                radius: 8
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Row {
                    id: overviewRow
                    anchors.centerIn: parent
                    spacing: 18

                    Text {
                        text: stock360Controller.ticker + "  " + root.fmt2(stock360Controller.lastPrice)
                        color: "#E5E7EB"
                        font.bold: true
                    }
                    Text {
                        text: root.fmtPct(stock360Controller.dailyChangePct)
                        color: root.pctColor(stock360Controller.dailyChangePct)
                    }
                    Text {
                        text: "52H: " + root.fmt2(stock360Controller.week52Low) + " - " + root.fmt2(stock360Controller.week52High)
                        color: "#9CA3AF"
                    }
                }
            }
        }

        Text {
            visible: stock360Controller.notFound
            text: "Hisse bulunamadı: " + stock360Controller.ticker
            color: root.colorLoss
        }

        // ---- Sekmeler ----
        TabBar {
            id: tabBar
            objectName: "tabBar"
            width: parent.width
            background: Rectangle { color: "#151D2C" }

            TabButton { text: "Fiyat & Teknik" }
            TabButton { text: "Bilanço & Rasyolar" }
            TabButton { text: "Ortaklık Yapısı" }
        }
    }

    Item {
        id: tabContent
        objectName: "tabContent"  // testte gerçek geometrinin (NaN/0 değil) doğrulanması için
        anchors.top: headerColumn.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.topMargin: 14
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        anchors.bottomMargin: 20

        // ---- Sekme 1: Fiyat Grafiği & Canlı İndikatörler ----
        Column {
            visible: tabBar.currentIndex === 0
            anchors.fill: parent
            spacing: 10

            Row {
                spacing: 8
                Repeater {
                    model: stock360Controller.rangeKeys
                    delegate: Button {
                        text: modelData
                        checkable: true
                        checked: stock360Controller.rangeKey === modelData
                        onClicked: stock360Controller.setRangeKey(modelData)
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 240
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                CandlestickChartItem {
                    anchors.fill: parent
                    anchors.margins: 8
                    bars: stock360Controller.candlestickBars
                }
            }

            Rectangle {
                width: parent.width
                height: 100
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    Text { text: "RSI14: " + root.fmt2(stock360Controller.rsi14); color: "#9CA3AF"; font.pixelSize: 11 }
                    LineChartItem {
                        width: parent.width
                        height: parent.height - 16
                        values: stock360Controller.rsiSeries
                        lineColor: "#8B5CF6"
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 100
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    Text {
                        text: "MACD: " + root.fmt2(stock360Controller.macdLine) + " / Sinyal: " + root.fmt2(stock360Controller.macdSignal)
                        color: "#9CA3AF"
                        font.pixelSize: 11
                    }
                    LineChartItem {
                        width: parent.width
                        height: parent.height - 16
                        values: stock360Controller.macdLineSeries
                        values2: stock360Controller.macdSignalSeries
                        lineColor: "#3B82F6"
                        lineColor2: "#F59E0B"
                    }
                }
            }
        }

        // ---- Sekme 2: Bilanço & Rasyolar ----
        Column {
            visible: tabBar.currentIndex === 1
            anchors.fill: parent
            spacing: 10

            Text {
                visible: stock360Controller.financialsError !== ""
                text: "Finansal veri alınamadı: " + stock360Controller.financialsError
                color: root.colorLoss
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Text {
                visible: stock360Controller.financialsError === ""
                text: "Dönem: " + stock360Controller.financialPeriod
                color: "#9CA3AF"
            }

            Row {
                visible: stock360Controller.financialsError === ""
                spacing: 12

                Repeater {
                    model: [
                        { label: "F/K", value: stock360Controller.fk },
                        { label: "PD/DD", value: stock360Controller.pddd },
                        { label: "FD/FAVÖK", value: stock360Controller.evFavok },
                        { label: "ROE", value: stock360Controller.roe, isPct: true }
                    ]
                    delegate: Rectangle {
                        width: 120
                        height: 60
                        radius: 10
                        color: "#151D2C"
                        border.color: "#26354A"
                        border.width: 1

                        Column {
                            anchors.centerIn: parent
                            spacing: 2
                            Text { text: modelData.label; color: "#9CA3AF"; font.pixelSize: 11; anchors.horizontalCenter: parent.horizontalCenter }
                            Text {
                                text: modelData.isPct ? ("%" + modelData.value.toFixed(1)) : modelData.value.toFixed(2)
                                color: "#E5E7EB"
                                font.bold: true
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }
                }
            }
        }

        // ---- Sekme 3: Ortaklık Yapısı (KAP) ----
        Column {
            visible: tabBar.currentIndex === 2
            anchors.fill: parent
            spacing: 10

            Text {
                visible: stock360Controller.shareholdersError !== ""
                text: "Ortaklık verisi alınamadı: " + stock360Controller.shareholdersError
                color: root.colorLoss
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Text {
                visible: stock360Controller.shareholdersError === ""
                text: "Halka Açıklık Oranı: %" + stock360Controller.freeFloatPct.toFixed(2)
                color: "#E5E7EB"
                font.bold: true
            }

            Repeater {
                model: stock360Controller.shareholderNames.length
                delegate: Row {
                    spacing: 12
                    Text { width: 220; text: stock360Controller.shareholderNames[index]; color: "#E5E7EB" }
                    Text { text: "%" + stock360Controller.shareholderRatios[index].toFixed(2); color: "#9CA3AF" }
                }
            }
        }
    }
}
