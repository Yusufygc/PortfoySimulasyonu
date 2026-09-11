import QtQuick
import QtQuick.Controls
import PortfoyCharts 1.0

// DashboardView (bkz. plan §7.3 madde 1) — 4 KPI kartı + pozisyon tablosu +
// varlık dağılımı donut. Veri: context property `dashboardController`
// (bkz. src/ui_qml/controllers/dashboard_controller.py).
Item {
    id: root
    anchors.fill: parent

    readonly property color colorProfit: "#10B981"
    readonly property color colorLoss: "#EF4444"
    function pctColor(value) { return value >= 0 ? colorProfit : colorLoss }
    function fmtMoney(value) { return value.toLocaleString(Qt.locale("tr_TR"), 'f', 2) }
    function fmtPct(value) { return (value >= 0 ? "+" : "") + value.toFixed(2) + "%" }

    // Değer Sayaçları (Rolling Numbers, bkz. plan §7.5) — portföy toplamı/K-Z
    // değiştikçe rakamlar sıçramak yerine animasyonla akar.
    property real animatedTotalValue: dashboardController.portfolio.totalValue
    property real animatedUnrealizedPl: dashboardController.portfolio.unrealizedPl
    Behavior on animatedTotalValue { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
    Behavior on animatedUnrealizedPl { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }

    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // ---- Üst KPI Paneli (4 Kart) ----
        Row {
            id: kpiRow
            width: parent.width
            spacing: 16
            height: 100

            Rectangle {
                id: kpiTotalValue
                width: (kpiRow.width - kpiRow.spacing * 3) / 4
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
                    Text { text: "Toplam Portföy Değeri"; color: "#9CA3AF"; font.pixelSize: 12 }
                    Text { text: root.fmtMoney(root.animatedTotalValue) + " ₺"; color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }
                    Text {
                        text: "Günlük: " + root.fmtPct(dashboardController.dailyChangePct)
                        color: root.pctColor(dashboardController.dailyChangePct)
                        font.pixelSize: 12
                    }
                }
            }

            Rectangle {
                id: kpiPl
                width: kpiTotalValue.width
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
                    Text { text: "Toplam Kâr / Zarar"; color: "#9CA3AF"; font.pixelSize: 12 }
                    Text {
                        text: root.fmtMoney(root.animatedUnrealizedPl) + " ₺"
                        color: root.pctColor(dashboardController.portfolio.unrealizedPl)
                        font.pixelSize: 18
                        font.bold: true
                    }
                    Text {
                        text: "Toplam: " + root.fmtPct(dashboardController.totalReturnPct)
                        color: root.pctColor(dashboardController.totalReturnPct)
                        font.pixelSize: 12
                    }
                }
            }

            Rectangle {
                id: kpiSharpe
                width: kpiTotalValue.width
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
                    Text { text: "Portföy Sharpe Oranı"; color: "#9CA3AF"; font.pixelSize: 12 }
                    Text { text: dashboardController.sharpeRatio.toFixed(2); color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }
                }
            }

            Rectangle {
                id: kpiBenchmark
                width: kpiTotalValue.width
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
                    Text { text: dashboardController.benchmarkLabel + " Relatif Getiri"; color: "#9CA3AF"; font.pixelSize: 12 }
                    Text {
                        text: root.fmtPct(dashboardController.benchmarkGapPct) + " Alfa"
                        color: root.pctColor(dashboardController.benchmarkGapPct)
                        font.pixelSize: 18
                        font.bold: true
                    }
                }
            }
        }

        // ---- Orta Bölüm (2 Kolon) ----
        Row {
            width: parent.width
            spacing: 16
            height: parent.height - kpiRow.height - parent.spacing

            Rectangle {
                id: positionsCard
                width: parent.width * 0.68
                height: parent.height
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                TableView {
                    id: positionsTable
                    anchors.fill: parent
                    anchors.margins: 12
                    columnSpacing: 1
                    rowSpacing: 1
                    model: dashboardController.portfolio.positionsModel

                    // Akıllı Tablo Hover'ı (bkz. plan §7.5): hücre üzerine gelindiğinde
                    // yumuşak parlama + son kolonda (Ağırlık %, satır sonu) "Detay"
                    // aksiyon butonu belirir. Gerçek drill-down navigasyonu henüz yok
                    // (sidebar/sayfa geçişi kurulmadı, bkz. WatchlistView'daki aynı not) —
                    // buton şimdilik sadece görsel etkileşim desenini gösterir.
                    delegate: Rectangle {
                        id: cellDelegate
                        required property int column
                        implicitWidth: 100
                        implicitHeight: 28
                        color: cellHover.hovered ? "#2A3D57" : "#1F2B3E"
                        Behavior on color { ColorAnimation { duration: 120 } }

                        HoverHandler { id: cellHover }

                        Text {
                            anchors.centerIn: parent
                            visible: !(cellDelegate.column === 5 && cellHover.hovered)
                            text: display !== undefined ? display : ""
                            color: "#E5E7EB"
                        }

                        Button {
                            anchors.centerIn: parent
                            visible: cellDelegate.column === 5 && cellHover.hovered
                            text: "Detay"
                            font.pixelSize: 10
                            implicitHeight: 22
                            implicitWidth: 70
                        }
                    }
                }
            }

            Rectangle {
                id: allocationCard
                width: parent.width - positionsCard.width - 16
                height: parent.height
                radius: 12
                color: "#151D2C"
                border.color: "#26354A"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Text { text: "Varlık Dağılımı"; color: "#9CA3AF"; font.pixelSize: 12 }

                    DonutChartItem {
                        id: allocationDonut
                        width: parent.width
                        height: parent.height - 80
                        weights: dashboardController.allocationWeights
                    }

                    Repeater {
                        model: dashboardController.allocationLabels.length
                        delegate: Row {
                            spacing: 6
                            Rectangle { width: 10; height: 10; radius: 5; color: Qt.hsla((index * 0.15) % 1.0, 0.6, 0.55, 1.0) }
                            Text {
                                text: dashboardController.allocationLabels[index] + " (" + dashboardController.allocationWeights[index].toFixed(1) + "%)"
                                color: "#9CA3AF"
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }
        }
    }
}
