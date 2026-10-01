import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls
import "theme"
import "components"
import "views"

ApplicationWindow {
    id: appWindow
    visible: true
    width: Math.min(1320, Math.max(960, Screen.desktopAvailableWidth * 0.90))
    height: Math.min(840, Math.max(600, Screen.desktopAvailableHeight * 0.90))
    minimumWidth: 960
    minimumHeight: 600
    title: "Portföy Simülasyonu - Modern QML & TradingView"
    color: Theme.bgPrimary

    Component.onCompleted: {
        x = Math.max(0, (Screen.desktopAvailableWidth - width) / 2)
        y = Math.max(0, (Screen.desktopAvailableHeight - height) / 2)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Üst Başlık Çubuğu & Piyasa Göstergeleri
        WindowHeader {
            id: header
            Layout.fillWidth: true
            onSearchRequested: function(ticker) {
                shellController.navigateTo(0)
                chartController.loadTicker(ticker)
            }
        }

        // Ana Gövde (Sidebar + İçerik)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Sol Navigasyon Barı
            Sidebar {
                id: sidebar
                Layout.fillHeight: true
            }

            // Sayfa İçerik Alanı
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Theme.bgPrimary

                StackLayout {
                    id: pageStack
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    currentIndex: shellController.activePage

                    // 0: Dashboard (Canlı QML & TradingView)
                    DashboardView {
                        id: dashboardView
                    }

                    // 1: Watchlist (Faz 4 - Canlı Çoklu Liste & Sparkline - Tembel Yükleme)
                    Loader {
                        id: watchlistLoader
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        active: shellController.activePage === 1 || (status === Loader.Ready)
                        source: "views/WatchlistView.qml"
                    }

                    // 2: Model Portföyler (Faz 6 - Canlı Sanal Simülasyon, Nakit Akışı & Al/Sat - Tembel Yükleme)
                    Loader {
                        id: modelPortfolioLoader
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        active: shellController.activePage === 2 || (status === Loader.Ready)
                        source: "views/ModelPortfolioView.qml"
                    }

                    // 3: Hisse 360 & Temel Analiz (Faz 5 - Canlı Rasyolar, Bilanço & KAP Ortaklık - Tembel Yükleme)
                    Loader {
                        id: stock360Loader
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        active: shellController.activePage === 3 || (status === Loader.Ready)
                        source: "views/Stock360View.qml"
                    }

                    // 4: Karşılaştırma Laboratuvarı (Faz 7 - Normalize Getiri & Risk Metrikleri - Tembel Yükleme)
                    Loader {
                        id: comparisonLoader
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        active: shellController.activePage === 4 || (status === Loader.Ready)
                        source: "views/ComparisonView.qml"
                    }

                    // 5: BIST Sinyal Tarayıcısı (Faz 7 - Algoritmik Strateji Taraması - Tembel Yükleme)
                    Loader {
                        id: screenerLoader
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        active: shellController.activePage === 5 || (status === Loader.Ready)
                        source: "views/ScreenerView.qml"
                    }

                    // 6: Finansal Planlama (Faz 8 - Bütçe, Hedefler & DCA Simülasyonu - Tembel Yükleme)
                    Loader {
                        id: planningLoader
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        active: shellController.activePage === 6 || (status === Loader.Ready)
                        source: "views/PlanningView.qml"
                    }

                    // 7: Optimizasyon (Faz 9)
                    PlaceholderView {
                        title: Strings.navOptimization
                        subtitle: "Faz 9 kapsamında Efficient Frontier saçılım eğrisi, ağırlık kısıtları ve rebalance önerileri eklenecektir."
                        iconName: "optimization"
                    }

                    // 8: AI Danışman (Faz 10)
                    PlaceholderView {
                        title: Strings.navAI + " Karar Destek Asistanı"
                        subtitle: "Faz 10 kapsamında interaktif chat, XAI portföy risk açıklamaları ve Function Calling durum takibi eklenecektir."
                        iconName: "ai"
                    }

                    // 9: Ayarlar (Faz 11)
                    PlaceholderView {
                        title: Strings.navSettings
                        subtitle: "Faz 11 kapsamında veritabanı bağlantı havuzu, Gemini API anahtarı ve tema yönetimi eklenecektir."
                        iconName: "settings"
                    }
                }
            }
        }
    }
}
