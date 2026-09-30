import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool isOpen: false

    anchors.fill: parent
    color: "#d0000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 99

    Behavior on opacity { NumberAnimation { duration: 200 } }

    MouseArea {
        anchors.fill: parent
        // Modal dışına tıklamayla kapanmayı önle
    }

    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 0.96
        height: parent.height * 0.94
        radius: Theme.radiusMd
        color: Theme.bgPrimary
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceSm
            spacing: Theme.spaceSm

            // Üst Bar: Toolbar + Kapat Butonu
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                TradingViewToolbar {
                    id: modalToolbar
                    Layout.fillWidth: true
                    chartView: modalChart
                    onToggleFullscreen: root.close()
                }

                ModernButton {
                    text: "✕ Kapat"
                    variant: "secondary"
                    implicitHeight: 36
                    onClicked: root.close()
                }
            }

            // Tam Ekran TradingView Grafiği
            TradingViewChart {
                id: modalChart
                Layout.fillWidth: true
                Layout.fillHeight: true
                ticker: chartController ? chartController.currentTicker : "OBAMS.IS"
            }
        }
    }

    function open() {
        isOpen = true
        if (modalChart && modalChart.isLoaded && chartController) {
            modalChart.loadStock(chartController.currentTicker)
        }
    }

    function close() {
        isOpen = false
    }
}
