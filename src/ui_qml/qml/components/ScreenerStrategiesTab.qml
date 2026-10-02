import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse Tarayıcı > Strateji Taraması sekmesi (RSI, MACD, Bollinger, 52 hafta vb.).
ColumnLayout {
    id: root
    spacing: Theme.spaceMd

        // 1. Filtre ve Kontrol Çubuğu Kartı (dar pencerede alt satıra sarar)
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: filterFlow.implicitHeight + Theme.spaceMd * 2
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            Flow {
                id: filterFlow
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceMd

                // Filtre Etiketi
                Row {
                    height: 36
                    spacing: Theme.spaceXs

                    ModernIcon {
                        name: "filter"
                        color: Theme.accent
                        size: 16
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: Strings.screenerFilterLabel + ":"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                // Strateji Seçici (ComboBox)
                ComboBox {
                    id: strategyCombo
                    width: Math.max(180, Math.min(320, filterFlow.width - 190))
                    height: 36
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
                            implicitWidth: 16
                            implicitHeight: 16
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
                    height: 36
                    width: filterFlow.width > 760 ? filterFlow.width - 560 : filterFlow.width
                    text: screenerController.statusText
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }
        }

        // 2. Sonuçlar Tablosu Kartı
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
                        text: Strings.screenerResultsTitle
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
                            Layout.preferredWidth: 100
                        }

                        Item {
                            Layout.preferredWidth: 70
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
                                    Layout.preferredWidth: 100
                                }

                                // Hızlı Grafik Butonu
                                Rectangle {
                                    Layout.preferredWidth: 70
                                    Layout.preferredHeight: 28
                                    radius: Theme.radiusXs
                                    color: btnChartMouse.containsMouse ? Theme.accent : Theme.bgInput
                                    border.color: btnChartMouse.containsMouse ? Theme.accent : Theme.borderSubtle
                                    border.width: 1
                                    z: 3

                                    RowLayout {
                                        anchors.centerIn: parent
                                        spacing: 4

                                        ModernIcon {
                                            name: "linechart"
                                            size: 11
                                            color: btnChartMouse.containsMouse ? "#ffffff" : Theme.accent
                                        }

                                        Text {
                                            text: Strings.btnChart
                                            color: btnChartMouse.containsMouse ? "#ffffff" : Theme.textPrimary
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            font.weight: Font.DemiBold
                                        }
                                    }

                                    MouseArea {
                                        id: btnChartMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            var clean = modelData.ticker.replace(".IS", "")
                                            chartController.loadTicker(clean)
                                            shellController.navigateTo(0)
                                        }
                                    }
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                z: 1
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var clean = modelData.ticker.replace(".IS", "")
                                    chartController.loadTicker(clean)
                                    stock360Controller.searchTicker(clean)
                                    shellController.navigateTo(3) // Tek tık: Hisse 360 detay
                                }
                                onDoubleClicked: {
                                    var clean = modelData.ticker.replace(".IS", "")
                                    chartController.loadTicker(clean)
                                    shellController.navigateTo(0) // Çift tık: TradingView Grafik
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
                            text: screenerController.statusText
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                        }
                    }
                }
            }
        }
}
