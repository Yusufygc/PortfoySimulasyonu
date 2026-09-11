import QtQuick
import QtQuick.Controls
import PortfoyCharts 1.0

// ScreenerView (bkz. plan §7.3 madde 3) — hazır filtre çipleri + sonuç listesi +
// satır seçiminde sağ panelde mini grafik/özet. Veri: context property
// `screenerController` (bkz. src/ui_qml/controllers/screener_controller.py).
//
// Not: Layout `headerColumn` (üstte, otomatik yükseklik) + `contentArea`
// (anchors ile kalan alanı dolduran) desenini kullanır — Stock360View'da
// bulunan "manuel yükseklik aritmetiği sessizce NaN üretebilir" hatasından
// (bkz. TRANSFORMATION_PLAN §9) ders alınarak.
Item {
    id: root
    anchors.fill: parent

    readonly property color colorAccent: "#3B82F6"
    readonly property color colorBullish: "#10B981"

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 10

        Text { text: "BIST Çoklu Sinyal Tarayıcısı"; color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }

        Row {
            spacing: 8
            Repeater {
                model: screenerController.filterKeys
                delegate: Button {
                    text: screenerController.filterLabels[index]
                    checkable: true
                    checked: screenerController.activeFilters.indexOf(modelData) !== -1
                    onClicked: screenerController.toggleFilter(modelData)
                }
            }
        }
    }

    Item {
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

        Row {
            anchors.fill: parent
            spacing: 16

            // ---- Sol: Sonuç Tablosu ----
            Rectangle {
                id: resultsCard
                width: parent.width * 0.62
                height: parent.height
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Flickable {
                    anchors.fill: parent
                    anchors.margins: 8
                    contentHeight: resultsColumn.height
                    clip: true

                    Column {
                        id: resultsColumn
                        width: parent.width
                        spacing: 1

                        Repeater {
                            model: screenerController.resultTickers.length
                            delegate: Rectangle {
                                width: resultsColumn.width
                                height: 36
                                color: screenerController.selectedTicker === screenerController.resultTickers[index] ? "#1F2B3E" : "transparent"

                                Row {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    spacing: 14

                                    Text { width: 80; anchors.verticalCenter: parent.verticalCenter; text: screenerController.resultTickers[index]; color: "#E5E7EB"; font.bold: true }
                                    Text { width: 80; anchors.verticalCenter: parent.verticalCenter; text: screenerController.resultClosePrices[index].toFixed(2); color: "#9CA3AF" }
                                    Rectangle {
                                        width: 50; height: 20; radius: 6; color: root.colorBullish; anchors.verticalCenter: parent.verticalCenter
                                        Text { anchors.centerIn: parent; text: screenerController.resultTrends[index]; color: "#0B0F19"; font.pixelSize: 10; font.bold: true }
                                    }
                                    Text {
                                        width: 260; anchors.verticalCenter: parent.verticalCenter
                                        text: screenerController.resultFilterLabels[index]
                                        color: "#9CA3AF"; font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: screenerController.selectTicker(screenerController.resultTickers[index])
                                }
                            }
                        }

                        Text {
                            visible: screenerController.resultTickers.length === 0
                            text: "Eşleşen hisse yok — filtre seçimini değiştirin."
                            color: "#9CA3AF"
                            leftPadding: 8
                            topPadding: 12
                        }
                    }
                }
            }

            // ---- Sağ: Mini Özet + Sparkline ----
            Rectangle {
                width: parent.width - resultsCard.width - 16
                height: parent.height
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text {
                        text: screenerController.selectedTicker !== "" ? screenerController.selectedTicker : "Bir hisse seçin"
                        color: "#E5E7EB"
                        font.bold: true
                        font.pixelSize: 16
                    }

                    Text { text: "Son Fiyat: " + screenerController.miniLastPrice.toFixed(2); color: "#9CA3AF"; font.pixelSize: 12 }
                    Text { text: "RSI14: " + screenerController.miniRsi14.toFixed(2); color: "#9CA3AF"; font.pixelSize: 12 }
                    Text {
                        text: "MACD: " + screenerController.miniMacdLine.toFixed(2) + " / Sinyal: " + screenerController.miniMacdSignal.toFixed(2)
                        color: "#9CA3AF"
                        font.pixelSize: 12
                    }

                    LineChartItem {
                        width: parent.width
                        height: 120
                        values: screenerController.sparklineValues
                        lineColor: root.colorAccent
                    }
                }
            }
        }
    }
}
