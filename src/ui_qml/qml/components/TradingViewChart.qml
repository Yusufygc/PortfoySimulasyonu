import QtQuick
import QtQuick.Controls
import QtWebEngine
import "../theme"

Item {
    id: root

    property string ticker: "BIST100"
    property bool isLoaded: false

    signal chartReady()

    clip: true

    WebEngineView {
        id: webView
        anchors.fill: parent
        backgroundColor: Theme.bgPrimary

        // Local template path
        url: Qt.resolvedUrl("../../assets/templates/tradingview_chart.html")

        settings.javascriptEnabled: true
        settings.localContentCanAccessRemoteUrls: true
        settings.localContentCanAccessFileUrls: true

        onLoadingChanged: function(loadRequest) {
            if (loadRequest.status === WebEngineView.LoadSucceededStatus) {
                root.isLoaded = true
                root.chartReady()
                // Initial data load if available
                if (chartController) {
                    chartController.loadTicker(root.ticker)
                }
            }
        }
    }

    // Connections to Python ChartController
    Connections {
        target: chartController

        function onChartDataLoaded(tickerName, jsonPayload) {
            if (!root.isLoaded) return
            root.ticker = tickerName

            const script = `
                (function() {
                    const data = JSON.parse(${JSON.stringify(jsonPayload)});
                    setTicker("${tickerName}");
                    setCandleData(data.candles, data.volumes);
                })();
            `
            webView.runJavaScript(script)
        }
    }

    // Public method to load ticker
    function loadStock(newTicker) {
        root.ticker = newTicker
        if (chartController) {
            chartController.loadTicker(newTicker)
        }
    }

    // Theme reaction
    Connections {
        target: Theme
        function onIsDarkChanged() {
            if (!root.isLoaded) return
            const script = `initChart("${root.ticker}", ${Theme.isDark});`
            webView.runJavaScript(script, function() {
                if (chartController) {
                    chartController.loadTicker(root.ticker)
                }
            })
        }
    }
}
