import QtQuick
import QtQuick.Controls
import QtWebEngine
import "../theme"

Item {
    id: root

    property string ticker: chartController ? chartController.currentTicker : "THYAO"
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

                // İlk veri yükleme ve başlangıç indikatörleri
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
                        setCandleData(data);
                    } catch (err) {
                        console.error("[TV Injection Error]:", err);
                    }
                })();
            `
            webView.runJavaScript(script, function() {
                // Aktif indikatörleri senkronize et
                syncIndicators();
            })
        }

        function onChartTypeChanged(chartType) {
            if (!root.isLoaded) return
            webView.runJavaScript(`setChartType("${chartType}");`);
        }

        function onIndicatorsChanged() {
            if (!root.isLoaded) return
            syncIndicators();
        }
    }

    // Aktif indikatörleri HTML motoruna aktarma
    function syncIndicators() {
        if (!chartController || !root.isLoaded) return;
        const activeList = chartController.activeIndicators || [];
        const allList = ["sma20", "sma50", "sma200", "ema20", "bb", "rsi", "macd", "markers"];
        allList.forEach(ind => {
            const active = activeList.indexOf(ind) !== -1;
            webView.runJavaScript(`toggleIndicator("${ind}", ${active ? "true" : "false"});`);
        });
    }

    // Public method to load ticker
    function loadStock(newTicker) {
        root.ticker = newTicker
        if (chartController) {
            chartController.loadTicker(newTicker)
        }
    }

    function setTimeframe(tf) {
        if (chartController) {
            chartController.setTimeframe(tf)
        }
    }

    function setChartType(type) {
        if (chartController) {
            chartController.setChartType(type)
        }
    }

    function toggleIndicator(ind, enabled) {
        if (chartController) {
            chartController.toggleIndicator(ind, enabled)
        }
    }

    function fitContent() {
        if (root.isLoaded) {
            webView.runJavaScript("fitContent();");
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
