import QtQuick
import QtQuick.Controls
import "views"

// d3 kabuk — basit üst düğmeyle Dashboard/Stock360/Screener/Watchlist arasında
// geçiş yapar (bkz. §7.1/§7.3/§9.5). Gerçek sidebar + dinamik sayfa yükleyici
// sonraki adımlarda bu geçici anahtarın yerini alacak.
// `visible` varsayılan false: otomatik testler pencere açmadan yükleyebilsin —
// gerçek çalıştırmada main.py bunu true'ya çeker.
ApplicationWindow {
    id: window
    visible: false
    width: 1280
    height: 800
    title: "Portföy Simülasyonu (QML)"
    color: "#0B0F19" // Background, bkz. plan §7.2

    Column {
        anchors.fill: parent

        Row {
            id: navBar
            width: parent.width
            height: 44
            spacing: 8
            padding: 8

            Button { text: "Dashboard"; onClicked: viewLoader.sourceComponent = dashboardComponent }
            Button { text: "Hisse 360"; onClicked: viewLoader.sourceComponent = stock360Component }
            Button { text: "Tarayıcı"; onClicked: viewLoader.sourceComponent = screenerComponent }
            Button { text: "İzleme Listesi"; onClicked: viewLoader.sourceComponent = watchlistComponent }
            Button { text: "Analiz"; onClicked: viewLoader.sourceComponent = analyticsComponent }
            Button { text: "Optimizasyon"; onClicked: viewLoader.sourceComponent = optimizationComponent }
            Button { text: "Simülasyon"; onClicked: viewLoader.sourceComponent = simulationComponent }
            Button { text: "Nakit Akış"; onClicked: viewLoader.sourceComponent = cashflowComponent }
            Button { text: "AI Danışman"; onClicked: viewLoader.sourceComponent = aiAdvisorComponent }
        }

        Loader {
            id: viewLoader
            width: parent.width
            height: parent.height - navBar.height
            sourceComponent: dashboardComponent

            // Sayfa geçişi: hafif fade & slide (bkz. plan §7.5) — her yeni view
            // yüklendiğinde 0 opaklık/10px aşağıdan başlayıp 180ms'de yerine oturur.
            onLoaded: {
                item.opacity = 0
                item.y = 10
                pageEnterAnimation.start()
            }

            ParallelAnimation {
                id: pageEnterAnimation
                NumberAnimation { target: viewLoader.item; property: "opacity"; to: 1; duration: 180; easing.type: Easing.OutCubic }
                NumberAnimation { target: viewLoader.item; property: "y"; to: 0; duration: 180; easing.type: Easing.OutCubic }
            }
        }
    }

    Component {
        id: dashboardComponent
        DashboardView {}
    }

    Component {
        id: stock360Component
        Stock360View {}
    }

    Component {
        id: screenerComponent
        ScreenerView {}
    }

    Component {
        id: watchlistComponent
        WatchlistView {}
    }

    Component {
        id: analyticsComponent
        AnalyticsView {}
    }

    Component {
        id: optimizationComponent
        OptimizationView {}
    }

    Component {
        id: simulationComponent
        SimulationView {}
    }

    Component {
        id: cashflowComponent
        CashflowView {}
    }

    Component {
        id: aiAdvisorComponent
        AiAdvisorView {}
    }
}
