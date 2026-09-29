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
    width: 1320
    height: 840
    minimumWidth: 1024
    minimumHeight: 680
    title: "Portföy Simülasyonu — Modern QML & TradingView"
    color: Theme.bgPrimary

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

                    // 1: Watchlist (Faz 4)
                    PlaceholderView {
                        title: "İzleme Listelerim (Watchlist)"
                        subtitle: "Faz 4 kapsamında çoklu liste sekmeleri, anlık fiyat alarmları ve mini sparkline grafikleri inşa edilecektir."
                        iconSymbol: "⭐"
                    }

                    // 2: Model Portföyler (Faz 6)
                    PlaceholderView {
                        title: "Model Portföyler"
                        subtitle: "Faz 6 kapsamında sanal portföy simülasyonu, nakit akışı ve BIST seans kontrollü al/sat dialogları eklenecektir."
                        iconSymbol: "💼"
                    }

                    // 3: Hisse 360 (Faz 5)
                    PlaceholderView {
                        title: "Hisse 360 & Temel Analiz"
                        subtitle: "Faz 5 kapsamında çeyreklik bilanço, rasyolar, KAP ortaklık yapısı ve serbest nakit akım grafikleri eklenecektir."
                        iconSymbol: "🎯"
                    }

                    // 4: Karşılaştırma Laboratuvarı (Faz 7)
                    PlaceholderView {
                        title: "Karşılaştırma Laboratuvarı"
                        subtitle: "Faz 7 kapsamında çoklu varlık normalize getiri grafikleri ve korelasyon ısı haritası eklenecektir."
                        iconSymbol: "⚖️"
                    }

                    // 5: Hisse Tarayıcı (Faz 7)
                    PlaceholderView {
                        title: "Hisse Tarayıcı (Screener)"
                        subtitle: "Faz 7 kapsamında F/K, RSI, temettü verimi ve hazır strateji filtreleri inşa edilecektir."
                        iconSymbol: "🔍"
                    }

                    // 6: Finansal Planlama (Faz 8)
                    PlaceholderView {
                        title: "Finansal Planlama & DCA Simülasyonu"
                        subtitle: "Faz 8 kapsamında kademeli alım (DCA) backtest simülatörü ve emeklilik tasarruf projeksiyonu eklenecektir."
                        iconSymbol: "📅"
                    }

                    // 7: Optimizasyon (Faz 9)
                    PlaceholderView {
                        title: "Markowitz Portföy Optimizasyonu"
                        subtitle: "Faz 9 kapsamında Efficient Frontier saçılım eğrisi, ağırlık kısıtları ve rebalance önerileri eklenecektir."
                        iconSymbol: "🛡️"
                    }

                    // 8: AI Danışman (Faz 10)
                    PlaceholderView {
                        title: "Gemini AI Karar Destek Asistanı"
                        subtitle: "Faz 10 kapsamında interaktif chat, XAI portföy risk açıklamaları ve Function Calling durum takibi eklenecektir."
                        iconSymbol: "🤖"
                    }

                    // 9: Ayarlar (Faz 11)
                    PlaceholderView {
                        title: "Uygulama Ayarları"
                        subtitle: "Faz 11 kapsamında veritabanı bağlantı havuzu, Gemini API anahtarı ve tema yönetimi eklenecektir."
                        iconSymbol: "⚙️"
                    }
                }
            }
        }
    }
}
