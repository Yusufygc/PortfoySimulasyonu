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

        onJavaScriptConsoleMessage: function(level, message, lineNumber, sourceID) {
            console.log("[TradingView JS]: " + message + " (line " + lineNumber + ")");
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
                    try {
                        let data = ${jsonPayload};
                        if (typeof data === "string") data = JSON.parse(data);
                        setTicker("${tickerName}");
                        if (data && data.candles && data.candles.length > 0) {
                            setCandleData(data.candles, data.volumes || []);
                        }
                    } catch (err) {
                        console.error("[TV Injection Error]:", err);
                    }
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
