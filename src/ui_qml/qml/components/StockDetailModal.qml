import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Item {
    id: root

    // Sinyaller
    signal openChartRequested(string ticker)
    signal openStock360Requested(string ticker)

    visible: (typeof stockDetailController !== "undefined") && stockDetailController.isOpen
    anchors.fill: parent
    z: 998

    // Emir formu durumu (yön, lot, fiyat, zaman) StockDetailOrderForm içindedir; sekme durumu StockDetailTabsPanel içindedir.
    Connections {
        target: (typeof stockDetailController !== "undefined") ? stockDetailController : null
        function onStockChanged() {
            orderForm.syncPrice()
        }
        function onTradeExecuted(success, message) {
            localToast.show(message, success)
        }
        function onExcelExported(success, message) {
            localToast.show(message, success)
        }
    }

    onVisibleChanged: {
        if (visible) {
            orderForm.resetTradeMoment()
            orderForm.syncPrice()
        }
    }

    // Yarı saydam koyu arka plan (Backdrop)
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.05, 0.07, 0.12, 0.75)

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (typeof stockDetailController !== "undefined") {
                    stockDetailController.close()
                }
            }
        }
    }

    // Modal Pencere Gövdesi
    Rectangle {
        id: modalBox
        // Dar pencerede modal tüm alanı kullanır; içerik tek sütuna iner ve kaydırılır
        readonly property bool stacked: width < 900
        width: Math.min(parent.width - 24, 1020)
        height: Math.min(parent.height - 24, 740)
        anchors.centerIn: parent
        color: Theme.bgSecondary
        radius: Theme.radiusMd
        border.color: Theme.borderSubtle
        border.width: 1
        clip: true

        // Tıklamaların arkaya geçmesini engelle
        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        Flickable {
            id: modalScroll
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            contentWidth: width
            contentHeight: Math.max(height, modalColumn.implicitHeight)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ModernScrollBar {}

        ColumnLayout {
            id: modalColumn
            width: modalScroll.width
            height: modalScroll.contentHeight
            spacing: Theme.spaceMd

            // =================================================================
            // 1. ÜST BAŞLIK VE KONTROL BARI
            // =================================================================
            StockDetailHeader {
                stacked: modalBox.stacked
                onOpenChartRequested: function(ticker) { root.openChartRequested(ticker) }
                onOpenStock360Requested: function(ticker) { root.openStock360Requested(ticker) }
                onCorporateActionRequested: corporateActionDialog.open(stockDetailController.ticker)
                onDividendRequested: dividendDialog.open(stockDetailController.ticker)
            }

            // Ayırıcı Çizgi
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderSubtle
            }

            // =================================================================
            // 2. POZİSYON KPI KARTLARI (4 KART)
            // =================================================================
            StockDetailKpiCards {
                Layout.fillWidth: true
                boxWidth: modalBox.width
            }

            // =================================================================
            // 3. İKİ SÜTUNLU GÖVDE: SOL TABLOLAR & SAĞ HIZLI EMİR FORMU
            // =================================================================
            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: modalBox.stacked ? 1 : 2
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd

                // -------------------------------------------------------------
                // SOL PANEL: TABLAR (İŞLEM GEÇMİŞİ & SERMAYE ARTIRIMLARI)
                // -------------------------------------------------------------
                StockDetailTabsPanel {
                }

                // -------------------------------------------------------------
                // SAĞ PANEL: HIZLI EMİR FORMU
                // -------------------------------------------------------------
                StockDetailOrderForm {
                    id: orderForm
                    stacked: modalBox.stacked
                }
            }
        }
        }
    }

    CorporateActionDialog {
        id: corporateActionDialog
        onApplied: function(message) {
            localToast.show(message, true)
            if (typeof stockDetailController !== "undefined") {
                stockDetailController.refreshData()
            }
        }
    }

    DividendDialog {
        id: dividendDialog
        onDividendsUpdated: function(message) {
            localToast.show(message, true)
        }
    }

    // Modal İçi Toast Bildirimi
    ToastNotification {
        id: localToast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 32
        z: 999
    }
}
