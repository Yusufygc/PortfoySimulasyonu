import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"

// Optimizasyon sonuç paneli: sekme çubuğu (Verimli Sınır / Ağırlıklar / Dengeleme) ve içerik kartı.
ColumnLayout {
        spacing: Theme.spaceMd
    // 2. SEKME ÇUBUĞU (3 SEKME)
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        Row {
            spacing: Theme.spaceXs

            Repeater {
                model: [
                { idx: 0, text: Strings.optTabFrontier, icon: "crosshair" },
                { idx: 1, text: Strings.optTabWeights, icon: "barchart" },
                { idx: 2, text: Strings.optTabRebalance, icon: "layers" }
                ]

                Rectangle {
                    width: tabRow.width + 20
                    height: 34
                    radius: Theme.radiusSm
                    color: optimizationController.activeTab === modelData.idx ? Theme.accent : (tabMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                    border.color: optimizationController.activeTab === modelData.idx ? Theme.accent : Theme.borderSubtle
                    border.width: 1

                    RowLayout {
                        id: tabRow
                        anchors.centerIn: parent
                        spacing: 6

                        ModernIcon {
                            name: modelData.icon
                            color: optimizationController.activeTab === modelData.idx ? Theme.textInverse : Theme.textSecondary
                            size: 13
                        }

                        Text {
                            text: modelData.text
                            color: optimizationController.activeTab === modelData.idx ? Theme.textInverse : Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: optimizationController.activeTab === modelData.idx ? Font.DemiBold : Font.Normal
                        }
                    }

                    MouseArea {
                        id: tabMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: optimizationController.setActiveTab(modelData.idx)
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }
    }

    // 3. İÇERİK KARTI (WebEngineView / Tablo)
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        radius: Theme.radiusMd
        color: Theme.bgCard
        border.color: Theme.borderCard
        border.width: 1
        clip: true

        // Yükleniyor Durumu
        ColumnLayout {
            anchors.centerIn: parent
            visible: optimizationController.isLoading
            spacing: Theme.spaceSm

            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: optimizationController.isLoading
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: Strings.optCalculating
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }
        }

        // Henüz Çalıştırılmadı Boş Durumu
        ColumnLayout {
            anchors.centerIn: parent
            visible: !optimizationController.hasResults && !optimizationController.isLoading
            spacing: Theme.spaceSm

            ModernIcon {
                Layout.alignment: Qt.AlignHCenter
                name: "optimization"
                size: 48
                color: Theme.textMuted
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: Strings.optEmptyTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: Font.Bold
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: Strings.optEmptySubtitle
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }
        }

        // SEKME 0: Verimli Sınır (Efficient Frontier) Saçılım Grafiği
        WebEngineView {
            id: frontierWebView
            anchors.fill: parent
            backgroundColor: Theme.bgCard
            visible: optimizationController.hasResults && !optimizationController.isLoading && optimizationController.activeTab === 0
            settings.javascriptEnabled: true
            settings.localContentCanAccessRemoteUrls: true

            Connections {
                target: optimizationController
                function onChartHtmlChanged() {
                    if (optimizationController.chartHtml !== "") {
                        frontierWebView.loadHtml(optimizationController.chartHtml)
                    }
                }
            }

            Component.onCompleted: {
                if (optimizationController.chartHtml !== "") {
                    frontierWebView.loadHtml(optimizationController.chartHtml)
                }
            }
        }

        // SEKME 1: Ağırlık Karşılaştırması Çubuk Grafiği
        WebEngineView {
            id: weightsWebView
            anchors.fill: parent
            backgroundColor: Theme.bgCard
            visible: optimizationController.hasResults && !optimizationController.isLoading && optimizationController.activeTab === 1
            settings.javascriptEnabled: true
            settings.localContentCanAccessRemoteUrls: true

            Connections {
                target: optimizationController
                function onWeightsChartHtmlChanged() {
                    if (optimizationController.weightsChartHtml !== "") {
                        weightsWebView.loadHtml(optimizationController.weightsChartHtml)
                    }
                }
            }

            Component.onCompleted: {
                if (optimizationController.weightsChartHtml !== "") {
                    weightsWebView.loadHtml(optimizationController.weightsChartHtml)
                }
            }
        }

        // SEKME 2: Yeniden Dengeleme (Rebalance) Öneri Tablosu
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceMd
            visible: optimizationController.hasResults && !optimizationController.isLoading && optimizationController.activeTab === 2
            spacing: Theme.spaceSm

            // Tablo Başlık Satırı
            Rectangle {
                Layout.fillWidth: true
                height: 36
                radius: Theme.radiusSm
                color: Theme.bgSecondary

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceMd
                    anchors.rightMargin: Theme.spaceMd
                    spacing: Theme.spaceSm

                    Text { Layout.preferredWidth: 80; text: Strings.optThSymbol; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { Layout.fillWidth: true; text: Strings.optThCompany; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: Strings.optThCurrentWeight; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: Strings.optThOptimalWeight; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: Strings.optThChange; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { Layout.preferredWidth: 100; horizontalAlignment: Text.AlignHCenter; text: Strings.optThAction; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { Layout.preferredWidth: 110; horizontalAlignment: Text.AlignRight; text: Strings.optThAmountDiff; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                    Text { Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight; text: Strings.optThEstShares; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold }
                }
            }

            // Tablo Satırları
            ListView {
                id: rebalanceList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: optimizationController.suggestions

                ScrollBar.vertical: ModernScrollBar {}

                delegate: Rectangle {
                    width: rebalanceList.width
                    height: 42
                    radius: Theme.radiusSm
                    color: rowMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary
                    border.color: Theme.borderSubtle
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceMd
                        anchors.rightMargin: Theme.spaceMd
                        spacing: Theme.spaceSm

                        // Sembol
                        Text {
                            Layout.preferredWidth: 80
                            text: (modelData.symbol || "").replace(/\.IS$/i, "").replace(/\.IS/g, "")
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                        }

                        // Şirket Adı
                        Text {
                            Layout.fillWidth: true
                            text: {
                                var cn = (modelData.companyName || modelData.symbol || "")
                                return cn.replace(/\.IS$/i, "").replace(/\.IS/g, "")
                            }
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            elide: Text.ElideRight
                        }

                        // Mevcut %
                        Text {
                            Layout.preferredWidth: 80
                            horizontalAlignment: Text.AlignRight
                            text: "%" + (modelData.currentWeight || 0).toFixed(2).replace('.', ',')
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }

                        // Optimum %
                        Text {
                            Layout.preferredWidth: 80
                            horizontalAlignment: Text.AlignRight
                            text: "%" + (modelData.optimalWeight || 0).toFixed(2).replace('.', ',')
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                        }

                        // Fark %
                        Text {
                            Layout.preferredWidth: 80
                            horizontalAlignment: Text.AlignRight
                            text: {
                                var ch = modelData.change || 0
                                var str = Math.abs(ch).toFixed(2).replace('.', ',')
                                if (ch > 0) return "+%" + str
                                if (ch < 0) return "-%" + str
                                return "%0,00"
                            }
                            color: modelData.change > 0 ? Theme.bullGreen : (modelData.change < 0 ? Theme.bearRed : Theme.textMuted)
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.Bold
                        }

                        // Aksiyon Rozeti (EKLE / AZALT / TUT)
                        Rectangle {
                            Layout.preferredWidth: 100
                            Layout.alignment: Qt.AlignHCenter
                            height: 24
                            radius: Theme.radiusXs
                            color: modelData.action === "EKLE" ? Theme.bullGreenSoft : (modelData.action === "AZALT" ? Theme.bearRedSoft : Theme.bgSecondary)
                            border.color: modelData.action === "EKLE" ? Theme.bullGreen : (modelData.action === "AZALT" ? Theme.bearRed : Theme.borderSubtle)
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData.action
                                color: modelData.action === "EKLE" ? Theme.bullGreen : (modelData.action === "AZALT" ? Theme.bearRed : Theme.textMuted)
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                            }
                        }

                        // Tahmini Tutar Farkı (₺)
                        Text {
                            Layout.preferredWidth: 110
                            horizontalAlignment: Text.AlignRight
                            text: {
                                var ad = modelData.amountDiff || 0
                                var str = Math.abs(ad).toLocaleString(Qt.locale("tr_TR"), "f", 2) + " ₺"
                                if (ad > 0) return "+" + str
                                if (ad < 0) return "-" + str
                                return "0,00 ₺"
                            }
                            color: modelData.amountDiff > 0 ? Theme.bullGreen : (modelData.amountDiff < 0 ? Theme.bearRed : Theme.textMuted)
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                        }

                        // Tahmini Lot
                        Text {
                            Layout.preferredWidth: 70
                            horizontalAlignment: Text.AlignRight
                            text: modelData.estShares > 0 ? modelData.estShares.toLocaleString(Qt.locale("tr_TR")) : "-"
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                    }
                }
            }
        }
    }
}
