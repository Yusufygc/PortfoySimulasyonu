import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    signal positionClicked(int stockId, string ticker)

    color: Theme.bgCard
    radius: Theme.radiusMd
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Başlık Çubuğu
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                name: "barchart"
                color: Theme.accent
                size: 16
            }

            Text {
                text: Strings.portfolioPositionsTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                font.letterSpacing: 0.5
                Layout.fillWidth: true
            }

            Text {
                text: portfolioController.positionsList.length + Strings.portfolioPositionsSuffix
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
        }

        // Tablo: dar alanda yatay kaydırılır (sütun hizası bozulmaz)
        Flickable {
            id: tableFlick
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: Math.max(width, 760)
            contentHeight: height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.HorizontalFlick
            ScrollBar.horizontal: ModernScrollBar {}

            ColumnLayout {
                width: tableFlick.contentWidth
                height: tableFlick.height
                spacing: Theme.spaceSm

        // Tablo Kolon Başlıkları
        Rectangle {
            Layout.fillWidth: true
            height: 32
            color: Theme.bgSecondary
            radius: Theme.radiusSm

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceMd
                anchors.rightMargin: Theme.spaceMd
                spacing: Theme.spaceSm

                // 1. HİSSE (Esnek kalan boşluğu doldurur)
                Text {
                    text: Strings.portfolioThTicker
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                    Layout.minimumWidth: 120
                }

                // 2. LOT
                Text {
                    text: Strings.portfolioThLot
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 70
                    Layout.minimumWidth: 70
                    Layout.maximumWidth: 70
                }

                // 3. ORT. MALİYET
                Text {
                    text: Strings.portfolioThAvgCost
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 95
                    Layout.minimumWidth: 95
                    Layout.maximumWidth: 95
                }

                // 4. GÜNCEL FİYAT
                Text {
                    text: Strings.portfolioThPrice
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 95
                    Layout.minimumWidth: 95
                    Layout.maximumWidth: 95
                }

                // 5. GÜNLÜK %
                Text {
                    text: Strings.portfolioThDailyPct
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 85
                    Layout.minimumWidth: 85
                    Layout.maximumWidth: 85
                }

                // 6. PİYASA DEĞERİ
                Text {
                    text: Strings.portfolioThValue
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 110
                    Layout.minimumWidth: 110
                    Layout.maximumWidth: 110
                }

                // 7. TOPLAM %
                Text {
                    text: Strings.portfolioThTotalPct
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 85
                    Layout.minimumWidth: 85
                    Layout.maximumWidth: 85
                }

                // 8. K/Z (₺)
                Text {
                    text: Strings.portfolioThPL
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 125
                    Layout.minimumWidth: 125
                    Layout.maximumWidth: 125
                }

                // 9. AĞIRLIK
                Text {
                    text: Strings.portfolioThWeight
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 115
                    Layout.minimumWidth: 115
                    Layout.maximumWidth: 115
                }
            }
        }

        // Pozisyonlar Listesi
        ListView {
            id: positionsListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: portfolioController.positionsList

            ScrollBar.vertical: ModernScrollBar {}

            delegate: Rectangle {
                id: rowDelegate
                width: positionsListView.width
                height: 46
                radius: Theme.radiusSm
                color: rowMouse.containsMouse ? Theme.bgCardHover : (index % 2 === 0 ? "transparent" : Theme.bgSecondary)

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceMd
                    anchors.rightMargin: Theme.spaceMd
                    spacing: Theme.spaceSm

                    // 1. Ticker & Şirket Adı
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 120
                        spacing: 1

                        Text {
                            text: modelData.ticker
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.DemiBold
                        }

                        Text {
                            text: modelData.companyName || ""
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            visible: modelData.companyName !== ""
                        }
                    }

                    // 2. Lot
                    Text {
                        text: Number(modelData.quantity).toLocaleString(Qt.locale("tr_TR"))
                        color: Theme.textPrimary
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 70
                        Layout.minimumWidth: 70
                        Layout.maximumWidth: 70
                    }

                    // 3. Ort. Maliyet
                    Text {
                        text: modelData.avgCost ? modelData.avgCost.toFixed(2).replace(".", ",") + " ₺" : "-"
                        color: Theme.textSecondary
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 95
                        Layout.minimumWidth: 95
                        Layout.maximumWidth: 95
                    }

                    // 4. Güncel Fiyat
                    Text {
                        text: modelData.currentPrice ? modelData.currentPrice.toFixed(2).replace(".", ",") + " ₺" : "-"
                        color: Theme.textPrimary
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 95
                        Layout.minimumWidth: 95
                        Layout.maximumWidth: 95
                    }

                    // 5. Günlük Değişim %
                    Text {
                        text: modelData.dailyChangeFormatted
                        color: modelData.dailyChangePct > 0 ? Theme.bullGreen : (modelData.dailyChangePct < 0 ? Theme.bearRed : Theme.textMuted)
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 85
                        Layout.minimumWidth: 85
                        Layout.maximumWidth: 85
                    }

                    // 6. Piyasa Değeri
                    Text {
                        text: Number(modelData.currentValue).toLocaleString(Qt.locale("tr_TR"), 'f', 2) + " ₺"
                        color: Theme.textPrimary
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 110
                        Layout.minimumWidth: 110
                        Layout.maximumWidth: 110
                    }

                    // 7. Toplam Getiri %
                    Text {
                        text: modelData.totalChangeFormatted
                        color: modelData.totalChangePct > 0 ? Theme.bullGreen : (modelData.totalChangePct < 0 ? Theme.bearRed : Theme.textMuted)
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 85
                        Layout.minimumWidth: 85
                        Layout.maximumWidth: 85
                    }

                    // 8. Kâr / Zarar (₺)
                    Text {
                        text: modelData.profitLossFormatted
                        color: modelData.profitLoss > 0 ? Theme.bullGreen : (modelData.profitLoss < 0 ? Theme.bearRed : Theme.textMuted)
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        horizontalAlignment: Text.AlignRight
                        Layout.preferredWidth: 125
                        Layout.minimumWidth: 125
                        Layout.maximumWidth: 125
                    }

                    // 9. Ağırlık (Bar + %)
                    RowLayout {
                        Layout.preferredWidth: 115
                        Layout.minimumWidth: 115
                        Layout.maximumWidth: 115
                        spacing: Theme.spaceXs

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 6
                            radius: 3
                            color: Theme.borderSubtle

                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                width: Math.max(0, Math.min(parent.width, parent.width * (modelData.weight / 100.0)))
                                radius: 3
                                color: Theme.accent
                            }
                        }

                        Text {
                            text: "%" + modelData.weight.toFixed(1).replace(".", ",")
                            color: Theme.textSecondary
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontXs
                            Layout.preferredWidth: 42
                            horizontalAlignment: Text.AlignRight
                        }
                    }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.positionClicked(modelData.stockId, modelData.ticker)
                }
            }
        }
            }
        }
    }
}
