import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse detayı sol panel: İşlem Geçmişi ve Sermaye Artırımları sekmeleri.
Rectangle {
    id: root
    // Aktif alt sekme: 0 = İşlem Geçmişi, 1 = Sermaye Artırımları
    property int activeTab: 0
    Layout.fillWidth: true
    Layout.fillHeight: true
    Layout.preferredWidth: 620
    Layout.preferredHeight: 380
    radius: Theme.radiusSm
    color: Theme.bgCard
    border.color: Theme.borderSubtle
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // Sekme Başlıkları
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                height: 32
                Layout.preferredWidth: 120
                radius: Theme.radiusSm
                color: root.activeTab === 0 ? Theme.primary : Theme.bgSecondary

                Text {
                    anchors.centerIn: parent
                    text: Strings.stockDetailTabTrades
                    color: root.activeTab === 0 ? "#FFFFFF" : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.activeTab = 0
                }
            }

            Rectangle {
                height: 32
                Layout.preferredWidth: 140
                radius: Theme.radiusSm
                color: root.activeTab === 1 ? Theme.primary : Theme.bgSecondary

                Text {
                    anchors.centerIn: parent
                    text: Strings.stockDetailTabCorpActions
                    color: root.activeTab === 1 ? "#FFFFFF" : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.activeTab = 1
                }
            }

            Item { Layout.fillWidth: true }
        }

        // Tab 1: İşlem Geçmişi Tablosu
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.activeTab === 0
            spacing: 6

            // Başlık Satırı
            Rectangle {
                Layout.fillWidth: true
                height: 28
                radius: 4
                color: Theme.bgSecondary

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8

                    Text { text: Strings.stockDetailThDate; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                    Text { text: Strings.stockDetailThTime; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 50 }
                    Text { text: Strings.stockDetailThType; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 70 }
                    Text { text: Strings.stockDetailThQty; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                    Text { text: Strings.stockDetailThPrice; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                    Text { text: Strings.stockDetailThTotal; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                }
            }

            // Liste
            ListView {
                id: tradesListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: (typeof stockDetailController !== "undefined") ? stockDetailController.tradesList : []
                spacing: 4

                delegate: Rectangle {
                    width: tradesListView.width
                    height: 32
                    radius: 4
                    color: index % 2 === 0 ? Theme.bgSecondary : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8

                        Text { text: modelData.date || ""; color: Theme.textSecondary; font.pixelSize: 11; Layout.preferredWidth: 80 }
                        Text { text: modelData.time || "-"; color: Theme.textMuted; font.pixelSize: 11; Layout.preferredWidth: 50 }

                        Rectangle {
                            Layout.preferredWidth: 56
                            Layout.preferredHeight: 20
                            radius: 10
                            color: modelData.isBuy ? Theme.bullGreenSoft : Theme.bearRedSoft

                            Text {
                                anchors.centerIn: parent
                                text: modelData.side || "ALIM"
                                color: modelData.isBuy ? Theme.bullGreen : Theme.bearRed
                                font.pixelSize: 10
                                font.weight: Font.Bold
                            }
                        }

                        Item { Layout.preferredWidth: 14 }

                        RowLayout {
                            Layout.preferredWidth: 80
                            Layout.alignment: Qt.AlignRight
                            spacing: 4

                            Text {
                                text: modelData.quantityStr || ((modelData.quantity || 0) + " Lot")
                                color: Theme.textPrimary
                                font.family: Theme.monoFontFamily
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignRight
                            }

                            Rectangle {
                                visible: Boolean(modelData.hasSplit)
                                width: 14
                                height: 14
                                radius: 7
                                color: Theme.accentSoft
                                ToolTip.visible: splitMouse.containsMouse
                                ToolTip.text: modelData.splitNote || ""
                                ToolTip.delay: 200

                                Text {
                                    anchors.centerIn: parent
                                    text: "B"
                                    color: Theme.accent
                                    font.pixelSize: 9
                                    font.weight: Font.Bold
                                }

                                MouseArea {
                                    id: splitMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }
                            }
                        }
                        Text { text: modelData.priceStr || "₺0.00"; color: Theme.textPrimary; font.family: Theme.monoFontFamily; font.pixelSize: 11; Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
                        Text { text: modelData.totalStr || "₺0.00"; color: Theme.textPrimary; font.family: Theme.monoFontFamily; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: tradesListView.count === 0
                    text: Strings.stockDetailEmptyTrades
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }

        // Tab 2: Sermaye Artırımları Tablosu
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.activeTab === 1
            spacing: 6

            // Başlık Satırı
            Rectangle {
                Layout.fillWidth: true
                height: 28
                radius: 4
                color: Theme.bgSecondary

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8

                    Text { text: Strings.stockDetailThDate; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 100 }
                    Text { text: Strings.stockDetailThType; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.preferredWidth: 120 }
                    Text { text: Strings.stockDetailThRatio; color: Theme.textMuted; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                }
            }

            ListView {
                id: corpListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: (typeof stockDetailController !== "undefined") ? stockDetailController.corpActionsList : []
                spacing: 4

                delegate: Rectangle {
                    width: corpListView.width
                    height: 32
                    radius: 4
                    color: index % 2 === 0 ? Theme.bgSecondary : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8

                        Text { text: modelData.date || ""; color: Theme.textSecondary; font.pixelSize: 11; Layout.preferredWidth: 100 }
                        Text { text: modelData.actionType || ""; color: Theme.textPrimary; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.preferredWidth: 120 }
                        Text { text: modelData.ratioStr || "%0.0"; color: Theme.bullGreen; font.pixelSize: 11; font.weight: Font.Bold; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: corpListView.count === 0
                    text: Strings.stockDetailEmptyCorp
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }
    }
}
