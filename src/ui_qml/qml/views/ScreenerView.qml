import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // 1. Üst Başlık Bölümü
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Text {
                text: Strings.screenerTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXl
                font.weight: Font.Bold
            }

            Text {
                text: Strings.screenerSubtitle
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
            }
        }

        // 2. Filtre ve Kontrol Çubuğu Kartı
        Rectangle {
            Layout.fillWidth: true
            height: 64
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceMd
                anchors.rightMargin: Theme.spaceMd
                spacing: Theme.spaceMd

                // Filtre Etiketi
                RowLayout {
                    spacing: Theme.spaceXs

                    ModernIcon {
                        name: "filter"
                        color: Theme.accent
                        size: 16
                    }

                    Text {
                        text: Strings.screenerFilterLabel + ":"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                    }
                }

                // Strateji Seçici (ComboBox)
                ComboBox {
                    id: strategyCombo
                    Layout.preferredWidth: 320
                    Layout.preferredHeight: 36
                    model: screenerController.filterOptions
                    textRole: "label"

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: strategyCombo.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1
                    }

                    contentItem: Text {
                        leftPadding: Theme.spaceSm
                        text: strategyCombo.displayText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        color: Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    onActivated: function(index) {
                        var opt = screenerController.filterOptions[index]
                        if (opt) {
                            screenerController.setFilter(opt.key)
                        }
                    }
                }

                // Taramayı Başlat Butonu
                Rectangle {
                    width: 150
                    height: 36
                    radius: Theme.radiusSm
                    color: screenerController.isRunning ? Theme.bgSecondary : (btnScanMouse.containsMouse ? Theme.accentHover : Theme.accent)
                    border.color: screenerController.isRunning ? Theme.borderSubtle : Theme.accent
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: Theme.spaceXs

                        BusyIndicator {
                            width: 16
                            height: 16
                            running: screenerController.isRunning
                            visible: screenerController.isRunning
                        }

                        ModernIcon {
                            name: "play"
                            color: Theme.textInverse
                            size: 14
                            visible: !screenerController.isRunning
                        }

                        Text {
                            text: screenerController.isRunning ? Strings.screenerRunning : Strings.screenerBtnScan
                            color: screenerController.isRunning ? Theme.textMuted : Theme.textInverse
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.DemiBold
                        }
                    }

                    MouseArea {
                        id: btnScanMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: screenerController.isRunning ? Qt.ArrowCursor : Qt.PointingHandCursor
                        enabled: !screenerController.isRunning
                        onClicked: screenerController.runScan()
                    }
                }

                // Durum Metni
                Text {
                    text: screenerController.statusText
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
        }

        // 3. Sonuçlar Tablosu Kartı
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceSm

                // Tablo Başlık Barı
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    ModernIcon {
                        name: "screener"
                        color: Theme.accent
                        size: 16
                    }

                    Text {
                        text: "TARAMA SONUÇLARI"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.5
                        Layout.fillWidth: true
                    }

                    Text {
                        text: Strings.screenerRowHint
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }
                }

                // Kolon Başlıkları
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

                        Text {
                            text: Strings.screenerThTicker
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                            Layout.preferredWidth: 140
                        }

                        Text {
                            text: Strings.screenerThStrategy
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }

                        Text {
                            text: Strings.screenerThPrice
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignRight
                            Layout.preferredWidth: 120
                        }
                    }
                }

                // Sonuçlar Listesi
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    // Liste
                    ListView {
                        id: resultsListView
                        anchors.fill: parent
                        clip: true
                        spacing: 2
                        model: screenerController.matchesList
                        visible: screenerController.matchesList.length > 0 && !screenerController.isRunning

                        ScrollBar.vertical: ModernScrollBar {}

                        delegate: Rectangle {
                            width: resultsListView.width
                            height: 44
                            radius: Theme.radiusSm
                            color: rowMouse.containsMouse ? Theme.bgCardHover : (index % 2 === 0 ? "transparent" : Theme.bgSecondary)

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceMd
                                anchors.rightMargin: Theme.spaceMd
                                spacing: Theme.spaceSm

                                // Hisse Kodu
                                RowLayout {
                                    Layout.preferredWidth: 140
                                    spacing: Theme.spaceSm

                                    Rectangle {
                                        width: 26
                                        height: 26
                                        radius: Theme.radiusXs
                                        color: Theme.accentSoft

                                        ModernIcon {
                                            anchors.centerIn: parent
                                            name: "target"
                                            color: Theme.accent
                                            size: 14
                                        }
                                    }

                                    Text {
                                        text: modelData.ticker
                                        color: Theme.accent
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontBase
                                        font.weight: Font.Bold
                                    }
                                }

                                // Strateji Adı
                                Text {
                                    text: modelData.filterLabel
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                // Son Fiyat
                                Text {
                                    text: modelData.closePrice
                                    color: Theme.textPrimary
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignRight
                                    Layout.preferredWidth: 120
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    chartController.loadTicker(modelData.ticker)
                                    stock360Controller.searchStock(modelData.ticker)
                                    shellController.navigateTo(3) // Hisse 360 sayfasına yönlendir
                                }
                            }
                        }
                    }

                    // Boş Durum
                    ColumnLayout {
                        anchors.centerIn: parent
                        visible: screenerController.matchesList.length === 0 && !screenerController.isRunning
                        spacing: Theme.spaceSm

                        ModernIcon {
                            Layout.alignment: Qt.AlignHCenter
                            name: "screener"
                            color: Theme.textMuted
                            size: 44
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.screenerEmptyTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.DemiBold
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.screenerEmptySubtitle
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                    }

                    // Taranıyor Durumu
                    ColumnLayout {
                        anchors.centerIn: parent
                        visible: screenerController.isRunning
                        spacing: Theme.spaceSm

                        BusyIndicator {
                            Layout.alignment: Qt.AlignHCenter
                            running: screenerController.isRunning
                        }

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: Strings.screenerRunning
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                        }
                    }
                }
            }
        }
    }
}
