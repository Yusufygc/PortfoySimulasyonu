import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Portföyüm pozisyon tablosu: BIST ve BIST dışı tüm pozisyonlar myPortfolioController.holdingsModel'den okunur.
// Sınıf sekmeleri (Tümü / BIST / ABD / Kripto / Emtia) modeli süzer; tutarlar seçili gösterim para biriminde,
// fiyatlar varlığın kendi para biriminde gösterilir.
ModernCard {
    id: root

    // BIST satırından işlem penceresi isteği; fiyatı pencere kendisi çözer
    signal tradeRequested(string ticker)
    // BIST dışı varlık satırından işlem / kaldırma isteği
    signal assetTradeRequested(int assetId)
    signal assetRemoveRequested(int assetId)

    readonly property var tabKeys: ["ALL", "BIST_STOCK", "US_STOCK", "CRYPTO", "PRECIOUS_METAL"]

    function tabLabel(key) {
        const name = key === "ALL" ? Strings.tabAll : Strings.allocationClassName(key)
        const count = myPortfolioController.tabCounts[key]
        return name + " (" + (count === undefined ? 0 : count) + ")"
    }

    // Grafik Genel Bakış sayfasındadır: sembol yüklenir ve sayfaya geçilir
    function openChart(ticker) {
        if (typeof chartController !== "undefined") {
            chartController.loadTicker(ticker)
        }
        shellController.navigateTo(0)
    }

    implicitHeight: tableColumn.implicitHeight + 36

    ColumnLayout {
        id: tableColumn
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Başlık ve özet
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: Strings.positionsTableTitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
                Layout.fillWidth: true
            }
            Text {
                text: Strings.positionsTableSubtitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
                elide: Text.ElideRight
                Layout.maximumWidth: 520
            }
        }

        // Sınıf sekmeleri (dar pencerede alt satıra sarılır)
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Repeater {
                model: root.tabKeys

                ModernButton {
                    text: root.tabLabel(modelData)
                    variant: myPortfolioController.activeClass === modelData ? "primary" : "ghost"
                    implicitHeight: 28
                    onClicked: myPortfolioController.setActiveClass(modelData)
                }
            }
        }

        Text {
            visible: myPortfolioController.activeClass === "PRECIOUS_METAL"
            text: Strings.myPortfolioMetalNote
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        // Tablo: dar pencerede yatay kaydırılır (sütun hizası bozulmaz)
        Flickable {
            id: tableFlick
            Layout.fillWidth: true
            implicitHeight: tableInner.implicitHeight + 10
            contentWidth: Math.max(width, 1250)
            contentHeight: tableInner.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.horizontal: ModernScrollBar {}

            ColumnLayout {
                id: tableInner
                width: tableFlick.contentWidth
                spacing: Theme.spaceSm

                // Başlık satırı
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 34
                    radius: Theme.radiusSm
                    color: Theme.bgInput

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8

                        Repeater {
                            model: [
                                { text: Strings.thSymbolCompany, width: 0, align: Text.AlignLeft },
                                { text: Strings.thQuantity, width: 90, align: Text.AlignRight },
                                { text: Strings.thAvgCost, width: 100, align: Text.AlignRight },
                                { text: Strings.thLastPrice, width: 100, align: Text.AlignRight },
                                { text: Strings.thDailyChange, width: 75, align: Text.AlignRight },
                                { text: Strings.thMarketValue, width: 125, align: Text.AlignRight },
                                { text: Strings.thPL, width: 120, align: Text.AlignRight },
                                { text: Strings.thPLPct, width: 80, align: Text.AlignRight },
                                { text: Strings.thWeight, width: 65, align: Text.AlignRight },
                                { text: Strings.thActions, width: 195, align: Text.AlignRight }
                            ]

                            Text {
                                required property var modelData
                                text: modelData.text
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                horizontalAlignment: modelData.align
                                Layout.fillWidth: modelData.width === 0
                                Layout.minimumWidth: modelData.width === 0 ? 170 : modelData.width
                                Layout.preferredWidth: modelData.width === 0 ? -1 : modelData.width
                                Layout.maximumWidth: modelData.width === 0 ? 100000 : modelData.width
                            }
                        }
                    }
                }

                Text {
                    visible: holdingsListView.count === 0
                    text: Strings.myPortfolioEmpty
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: Theme.spaceMd
                    Layout.bottomMargin: Theme.spaceMd
                }

                // Pozisyon satırları
                ListView {
                    id: holdingsListView
                    Layout.fillWidth: true
                    implicitHeight: count * 46
                    model: myPortfolioController.holdingsModel
                    interactive: false

                    delegate: Rectangle {
                        id: row
                        width: holdingsListView.width
                        height: 44
                        radius: Theme.radiusSm
                        color: rowMouse.containsMouse ? Theme.bgCardHover : "transparent"

                        Behavior on color { ColorAnimation { duration: 120 } }

                        // Satır tıklaması (BIST): hisse detayı; düğmeler bu alanın üstündedir
                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: model.isBist ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                if (model.isBist && typeof stockDetailController !== "undefined") {
                                    stockDetailController.openStock(model.symbol)
                                }
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            // Sembol ve ad (+ Tümü sekmesinde sınıf)
                            Column {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 170
                                spacing: 2
                                Text {
                                    text: model.symbol
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }
                                Text {
                                    text: myPortfolioController.activeClass === "ALL"
                                          ? model.name + " • " + Strings.allocationClassName(model.classKey)
                                          : model.name
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.textMuted
                                    elide: Text.ElideRight
                                    width: 220
                                }
                            }

                            Text {
                                text: model.quantity
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.textSecondary
                                Layout.preferredWidth: 90
                                Layout.minimumWidth: 90
                                Layout.maximumWidth: 90
                                horizontalAlignment: Text.AlignRight
                            }

                            Text {
                                text: model.avgCost
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.textSecondary
                                Layout.preferredWidth: 100
                                Layout.minimumWidth: 100
                                Layout.maximumWidth: 100
                                horizontalAlignment: Text.AlignRight
                            }

                            Text {
                                text: model.price
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                                Layout.preferredWidth: 100
                                Layout.minimumWidth: 100
                                Layout.maximumWidth: 100
                                horizontalAlignment: Text.AlignRight
                            }

                            Text {
                                text: model.dailyChange
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.DemiBold
                                color: model.dailyChange === "-" ? Theme.textMuted : (model.isDailyUp ? Theme.bullGreen : Theme.bearRed)
                                Layout.preferredWidth: 75
                                Layout.minimumWidth: 75
                                Layout.maximumWidth: 75
                                horizontalAlignment: Text.AlignRight
                            }

                            // Değer: değerlenemeyen pozisyon maliyet bedeliyle gösterilir ve işaretlenir
                            Column {
                                Layout.preferredWidth: 125
                                Layout.minimumWidth: 125
                                Layout.maximumWidth: 125
                                spacing: 0
                                Text {
                                    anchors.right: parent.right
                                    text: model.value
                                    font.family: Theme.monoFontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                }
                                Text {
                                    anchors.right: parent.right
                                    visible: !model.isPriced
                                    text: Strings.holdingUnpriced
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    color: Theme.warning
                                }
                            }

                            Text {
                                text: model.pl
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.Bold
                                color: model.isUp ? Theme.bullGreen : Theme.bearRed
                                Layout.preferredWidth: 120
                                Layout.minimumWidth: 120
                                Layout.maximumWidth: 120
                                horizontalAlignment: Text.AlignRight
                            }

                            Text {
                                text: model.plPct
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.Bold
                                color: model.plPct === "-" ? Theme.textMuted : (model.isUp ? Theme.bullGreen : Theme.bearRed)
                                Layout.preferredWidth: 80
                                Layout.minimumWidth: 80
                                Layout.maximumWidth: 80
                                horizontalAlignment: Text.AlignRight
                            }

                            Text {
                                text: model.weight
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.textSecondary
                                Layout.preferredWidth: 65
                                Layout.minimumWidth: 65
                                Layout.maximumWidth: 65
                                horizontalAlignment: Text.AlignRight
                            }

                            // Eylemler: BIST satırı Grafik / Detay / İşlem; BIST dışı satır İşlem / Kaldır
                            RowLayout {
                                Layout.preferredWidth: 195
                                Layout.minimumWidth: 195
                                Layout.maximumWidth: 195
                                spacing: 4
                                Layout.alignment: Qt.AlignRight

                                Item { Layout.fillWidth: true }

                                ModernButton {
                                    visible: model.isBist
                                    text: Strings.btnChart
                                    variant: "ghost"
                                    implicitHeight: 26
                                    implicitWidth: 60
                                    onClicked: root.openChart(model.symbol)
                                }

                                ModernButton {
                                    visible: model.isBist
                                    text: Strings.dashboardDetailButton
                                    variant: "ghost"
                                    implicitHeight: 26
                                    implicitWidth: 55
                                    onClicked: {
                                        if (typeof stockDetailController !== "undefined") {
                                            stockDetailController.openStock(model.symbol)
                                        }
                                    }
                                }

                                ModernButton {
                                    visible: !model.isBist
                                    text: Strings.assetRemove
                                    variant: "ghost"
                                    implicitHeight: 26
                                    implicitWidth: 70
                                    onClicked: root.assetRemoveRequested(model.refId)
                                }

                                ModernButton {
                                    text: Strings.btnTrade
                                    variant: "secondary"
                                    implicitHeight: 26
                                    implicitWidth: 55
                                    onClicked: model.isBist ? root.tradeRequested(model.symbol) : root.assetTradeRequested(model.refId)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
