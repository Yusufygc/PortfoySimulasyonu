import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // 1. Simülasyon Parametre Formu Kartı
        Rectangle {
            Layout.fillWidth: true
            height: 72
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceMd

                // Hisseler
                ColumnLayout {
                    spacing: 2
                    Layout.preferredWidth: 160

                    Text {
                        text: Strings.dcaTickersLabel
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }

                    TextField {
                        id: txtTickers
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        text: "THYAO FROTO"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        leftPadding: Theme.spaceSm
                        rightPadding: Theme.spaceSm

                        background: Rectangle {
                            color: Theme.bgInput
                            radius: Theme.radiusSm
                            border.color: Theme.borderSubtle
                            border.width: 1
                        }
                    }
                }

                // Aylık Katkı
                ColumnLayout {
                    spacing: 2
                    Layout.preferredWidth: 120

                    Text {
                        text: Strings.dcaAmountLabel
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }

                    TextField {
                        id: txtAmount
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        text: "5000"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        leftPadding: Theme.spaceSm
                        rightPadding: Theme.spaceSm
                        inputMethodHints: Qt.ImhFormattedNumbersOnly

                        background: Rectangle {
                            color: Theme.bgInput
                            radius: Theme.radiusSm
                            border.color: Theme.borderSubtle
                            border.width: 1
                        }
                    }
                }

                // Başlangıç Tarihi
                ColumnLayout {
                    spacing: 2
                    Layout.preferredWidth: 110

                    Text {
                        text: "Başlangıç (Tarih):"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }

                    TextField {
                        id: txtStart
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        text: "2023-01-01"
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        leftPadding: Theme.spaceSm
                        rightPadding: Theme.spaceSm

                        background: Rectangle {
                            color: Theme.bgInput
                            radius: Theme.radiusSm
                            border.color: Theme.borderSubtle
                            border.width: 1
                        }
                    }
                }

                // Bitiş Tarihi
                ColumnLayout {
                    spacing: 2
                    Layout.preferredWidth: 110

                    Text {
                        text: "Bitiş (Tarih):"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }

                    TextField {
                        id: txtEnd
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        text: {
                            var today = new Date()
                            var yyyy = today.getFullYear()
                            var mm = String(today.getMonth() + 1).padStart(2, '0')
                            var dd = String(today.getDate()).padStart(2, '0')
                            return yyyy + "-" + mm + "-" + dd
                        }
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        leftPadding: Theme.spaceSm
                        rightPadding: Theme.spaceSm

                        background: Rectangle {
                            color: Theme.bgInput
                            radius: Theme.radiusSm
                            border.color: Theme.borderSubtle
                            border.width: 1
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Simülasyonu Çalıştır Butonu
                Rectangle {
                    width: 160
                    height: 36
                    radius: Theme.radiusSm
                    color: planningController.dcaIsRunning ? Theme.bgSecondary : (btnRunDcaMouse.containsMouse ? Theme.accentHover : Theme.accent)
                    border.color: planningController.dcaIsRunning ? Theme.borderSubtle : Theme.accent
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: Theme.spaceXs

                        BusyIndicator {
                            width: 16
                            height: 16
                            running: planningController.dcaIsRunning
                            visible: planningController.dcaIsRunning
                        }

                        ModernIcon {
                            name: "play"
                            color: Theme.textInverse
                            size: 14
                            visible: !planningController.dcaIsRunning
                        }

                        Text {
                            text: planningController.dcaIsRunning ? "Hesaplanıyor..." : Strings.dcaBtnRun
                            color: planningController.dcaIsRunning ? Theme.textMuted : Theme.textInverse
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.DemiBold
                        }
                    }

                    MouseArea {
                        id: btnRunDcaMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: planningController.dcaIsRunning ? Qt.ArrowCursor : Qt.PointingHandCursor
                        enabled: !planningController.dcaIsRunning
                        onClicked: {
                            var amt = parseFloat(txtAmount.text.replace(",", ".")) || 5000.0
                            planningController.runDcaBacktest(
                                txtTickers.text.trim(),
                                amt,
                                txtStart.text.trim(),
                                txtEnd.text.trim()
                            )
                        }
                    }
                }
            }
        }

        // 2. DCA KPI Kartları Şeridi
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            // Toplam Yatırılan
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusSm
                        color: Theme.accentSoft

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "wallet"
                            color: Theme.accent
                            size: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.dcaKpiInvested
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                        Text {
                            text: planningController.dcaTotalInvested
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                    }
                }
            }

            // Nihai Portföy Değeri
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusSm
                        color: Theme.bullGreenSoft

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "coins"
                            color: Theme.bullGreen
                            size: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.dcaKpiFinal
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                        Text {
                            text: planningController.dcaFinalValue
                            color: Theme.bullGreen
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                    }
                }
            }

            // Toplam Getiri %
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusSm
                        color: planningController.dcaReturnPct >= 0 ? Theme.bullGreenSoft : Theme.bearRedSoft

                        ModernIcon {
                            anchors.centerIn: parent
                            name: planningController.dcaReturnPct >= 0 ? "trendingup" : "trendingdown"
                            color: planningController.dcaReturnPct >= 0 ? Theme.bullGreen : Theme.bearRed
                            size: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.dcaKpiReturn
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                        Text {
                            text: planningController.dcaReturnFormatted
                            color: planningController.dcaReturnPct >= 0 ? Theme.bullGreen : Theme.bearRed
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                    }
                }
            }

            // Katkı Sayısı
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusSm
                        color: Theme.bgSecondary

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "calendar"
                            color: Theme.textSecondary
                            size: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.dcaKpiCount
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                        Text {
                            text: planningController.dcaContributionCount + " Ay"
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                    }
                }
            }
        }

        // 3. Alt Bölüm: Hisse Lot Dağılımı + Değer Eğrisi Grafiği
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spaceMd

            // Sol Panel: Biriken Hisseler (260px)
            Rectangle {
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                color: Theme.bgCard
                radius: Theme.radiusMd
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        ModernIcon {
                            name: "barchart"
                            color: Theme.accent
                            size: 16
                        }

                        Text {
                            text: Strings.dcaSharesTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    ListView {
                        id: sharesListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: planningController.dcaSharesList

                        ScrollBar.vertical: ModernScrollBar {}

                        delegate: Rectangle {
                            width: sharesListView.width
                            height: 40
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceSm
                                anchors.rightMargin: Theme.spaceSm

                                Text {
                                    text: modelData.ticker
                                    color: Theme.accent
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.weight: Font.Bold
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: modelData.quantityFormatted
                                    color: Theme.textPrimary
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }
                            }
                        }
                    }
                }
            }

            // Sağ Panel: Portföy Değer Eğrisi
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

                    // Başlık Şeridi
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        ModernIcon {
                            name: "trendingup"
                            color: Theme.bullGreen
                            size: 16
                        }

                        Text {
                            text: Strings.dcaChartTitle
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        WebEngineView {
                            id: dcaWebView
                            anchors.fill: parent
                            backgroundColor: Theme.bgCard
                            visible: planningController.dcaChartHtml !== ""

                            settings.javascriptEnabled: true
                            settings.localContentCanAccessRemoteUrls: true

                            Component.onCompleted: {
                                if (planningController.dcaChartHtml !== "") {
                                    dcaWebView.loadHtml(planningController.dcaChartHtml)
                                }
                            }

                            onVisibleChanged: {
                                if (visible && planningController.dcaChartHtml !== "") {
                                    dcaWebView.loadHtml(planningController.dcaChartHtml)
                                }
                            }

                            Connections {
                                target: planningController
                                function onDcaChanged() {
                                    if (planningController.dcaChartHtml !== "") {
                                        dcaWebView.loadHtml(planningController.dcaChartHtml)
                                    }
                                }
                            }
                        }

                        // Boş Durum
                        ColumnLayout {
                            anchors.centerIn: parent
                            visible: planningController.dcaChartHtml === "" && !planningController.dcaIsRunning
                            spacing: Theme.spaceSm

                            ModernIcon {
                                Layout.alignment: Qt.AlignHCenter
                                name: "areachart"
                                color: Theme.textMuted
                                size: 44
                            }

                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: "Simülasyon çalıştırılmadı"
                                color: Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.weight: Font.DemiBold
                            }

                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: "Hisse kodlarını ve katkı tutarını girip 'Simülasyonu Çalıştır' butonuna basın."
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                            }
                        }
                    }
                }
            }
        }
    }
}
