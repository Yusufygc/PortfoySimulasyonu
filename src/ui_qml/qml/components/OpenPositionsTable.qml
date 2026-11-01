import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    // Pozisyon satırından işlem penceresi açma isteği (pencere üst görünümde durur)
    signal tradeRequested(string ticker, real price)

    // Grafik Genel Bakış sayfasındadır: sembol yüklenir ve sayfaya geçilir
    function openChart(ticker) {
        if (typeof chartController !== "undefined") {
            chartController.loadTicker(ticker)
        }
        shellController.navigateTo(0)
    }

    Layout.fillWidth: true
    implicitHeight: tableColumn.implicitHeight + 36

    ColumnLayout {
        id: tableColumn
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Tablo Üst Başlık & Özet
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
            }
        }

        // Tablo: dar pencerede yatay kaydırılır (sütun hizası bozulmaz)
        Flickable {
            id: tableFlick
            Layout.fillWidth: true
            implicitHeight: tableInner.implicitHeight + 10
            contentWidth: Math.max(width, 1130)
            contentHeight: tableInner.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.horizontal: ModernScrollBar {}

            ColumnLayout {
                id: tableInner
                width: tableFlick.contentWidth
                spacing: Theme.spaceSm

        // Tablo Başlık Satırı
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

                Text {
                    text: Strings.thSymbolCompany
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.fillWidth: true
                    Layout.minimumWidth: 160
                }
                Text {
                    text: Strings.thQuantity
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 70
                    Layout.minimumWidth: 70
                    Layout.maximumWidth: 70
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thAvgCost
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 85
                    Layout.minimumWidth: 85
                    Layout.maximumWidth: 85
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thLastPrice
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 85
                    Layout.minimumWidth: 85
                    Layout.maximumWidth: 85
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thDailyChange
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 75
                    Layout.minimumWidth: 75
                    Layout.maximumWidth: 75
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thMarketValue
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 115
                    Layout.minimumWidth: 115
                    Layout.maximumWidth: 115
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thPLTRY
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 110
                    Layout.minimumWidth: 110
                    Layout.maximumWidth: 110
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thPLPct
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 75
                    Layout.minimumWidth: 75
                    Layout.maximumWidth: 75
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thWeight
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 65
                    Layout.minimumWidth: 65
                    Layout.maximumWidth: 65
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: Strings.thActions
                    color: Theme.textMuted
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    Layout.preferredWidth: 195
                    Layout.minimumWidth: 195
                    Layout.maximumWidth: 195
                    horizontalAlignment: Text.AlignRight
                }
            }
        }

        // Dinamik Pozisyon Satırları (ListView)
        ListView {
            id: positionsListView
            Layout.fillWidth: true
            implicitHeight: count * 42
            model: dashboardController.positionsModel
            interactive: false

            delegate: Rectangle {
                id: posRow
                width: positionsListView.width
                height: 40
                radius: Theme.radiusSm

                // Flash Animation: Fiyat arttığında yeşil, düştüğünde kırmızı yanıp sönme
                color: {
                    if (model.flashState === 1) return Theme.bullGreenSoft
                    if (model.flashState === 2) return Theme.bearRedSoft
                    return rowMouse.containsMouse ? Theme.bgCardHover : "transparent"
                }

                Behavior on color { ColorAnimation { duration: 250 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    // Sembol & İsim
                    Column {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 160
                        spacing: 2
                        Text {
                            text: (model.ticker || "").replace(/\.IS$/i, "")
                            font.family: Theme.monoFontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }
                        Text {
                            text: (model.companyName || "").replace(/\.IS$/i, "")
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                            elide: Text.ElideRight
                            width: 150
                        }
                    }

                    // Lot
                    Text {
                        text: model.quantity
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textSecondary
                        Layout.preferredWidth: 70
                        Layout.minimumWidth: 70
                        Layout.maximumWidth: 70
                        horizontalAlignment: Text.AlignRight
                    }

                    // Maliyet
                    Text {
                        text: model.avgCost
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textSecondary
                        Layout.preferredWidth: 85
                        Layout.minimumWidth: 85
                        Layout.maximumWidth: 85
                        horizontalAlignment: Text.AlignRight
                    }

                    // Son Fiyat (Flash durumunda renklendirme)
                    Text {
                        text: model.currentPrice
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: model.flashState === 1 ? Theme.bullGreen : (model.flashState === 2 ? Theme.bearRed : Theme.textPrimary)
                        Layout.preferredWidth: 85
                        Layout.minimumWidth: 85
                        Layout.maximumWidth: 85
                        horizontalAlignment: Text.AlignRight
                    }

                    // Günlük Fark %
                    Text {
                        text: model.dailyDiff
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        color: model.dailyDiff.indexOf("+") !== -1 ? Theme.bullGreen : Theme.bearRed
                        Layout.preferredWidth: 75
                        Layout.minimumWidth: 75
                        Layout.maximumWidth: 75
                        horizontalAlignment: Text.AlignRight
                    }

                    // Piyasa Değeri
                    Text {
                        text: model.marketValue
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                        Layout.preferredWidth: 115
                        Layout.minimumWidth: 115
                        Layout.maximumWidth: 115
                        horizontalAlignment: Text.AlignRight
                    }

                    // K/Z ₺
                    Text {
                        text: model.unrealizedPL
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: model.isUp ? Theme.bullGreen : Theme.bearRed
                        Layout.preferredWidth: 110
                        Layout.minimumWidth: 110
                        Layout.maximumWidth: 110
                        horizontalAlignment: Text.AlignRight
                    }

                    // K/Z %
                    Text {
                        text: model.unrealizedPLPct
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: model.isUp ? Theme.bullGreen : Theme.bearRed
                        Layout.preferredWidth: 75
                        Layout.minimumWidth: 75
                        Layout.maximumWidth: 75
                        horizontalAlignment: Text.AlignRight
                    }

                    // Ağırlık
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

                    // Aksiyon Butonları (Al/Sat & Grafik)
                    RowLayout {
                        Layout.preferredWidth: 195
                        Layout.minimumWidth: 195
                        Layout.maximumWidth: 195
                        spacing: 4
                        Layout.alignment: Qt.AlignRight

                        ModernButton {
                            text: Strings.btnChart
                            variant: "ghost"
                            implicitHeight: 26
                            implicitWidth: 60
                            onClicked: root.openChart(model.ticker)
                        }

                        ModernButton {
                            text: Strings.dashboardDetailButton
                            variant: "ghost"
                            implicitHeight: 26
                            implicitWidth: 55
                            onClicked: {
                                if (typeof stockDetailController !== "undefined") {
                                    stockDetailController.openStock(model.ticker)
                                }
                            }
                        }

                        ModernButton {
                            text: Strings.btnTrade
                            variant: "secondary"
                            implicitHeight: 26
                            implicitWidth: 55
                            onClicked: {
                                const p = parseFloat(model.currentPrice.replace("₺", "").replace(".", "").replace(",", ".")) || 0.0
                                root.tradeRequested(model.ticker, p)
                            }
                        }
                    }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof stockDetailController !== "undefined") {
                            stockDetailController.openStock(model.ticker)
                        }
                    }
                }
            }
        }
            }
        }
    }
}
