import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtWebEngine
import "../theme"

Rectangle {
    id: root

    color: Theme.bgCard
    radius: Theme.radiusMd
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Üst Bar: Başlık ve Hızlı Dönem Seçici
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                name: "compare"
                color: Theme.accent
                size: 18
            }

            Text {
                text: Strings.compareTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: Font.DemiBold
            }

            Item { Layout.fillWidth: true }

            // Hızlı Dönem Butonları
            Row {
                spacing: Theme.spaceXs

                Repeater {
                    model: ["1A", "3A", "6A", "1Y", "YBB", "Tümü"]

                    Rectangle {
                        width: 44
                        height: 28
                        radius: Theme.radiusSm
                        color: comparisonController.periodLabel === modelData ? Theme.accent : (btnMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                        border.color: comparisonController.periodLabel === modelData ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            color: comparisonController.periodLabel === modelData ? Theme.textInverse : Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: comparisonController.periodLabel === modelData ? Font.Bold : Font.Normal
                        }

                        MouseArea {
                            id: btnMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: comparisonController.setPeriod(modelData)
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // Grafik veya Boş Durum
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // WebEngineView Grafik
            WebEngineView {
                id: chartWebView
                anchors.fill: parent
                backgroundColor: Theme.bgCard
                visible: comparisonController.chartHtml !== "" && !comparisonController.isLoading

                settings.javascriptEnabled: true
                settings.localContentCanAccessRemoteUrls: true

                Connections {
                    target: comparisonController
                    function onChartHtmlChanged() {
                        if (comparisonController.chartHtml !== "") {
                            chartWebView.loadHtml(comparisonController.chartHtml)
                        }
                    }
                }
            }

            // Yükleniyor Durumu
            ColumnLayout {
                anchors.centerIn: parent
                visible: comparisonController.isLoading
                spacing: Theme.spaceSm

                BusyIndicator {
                    Layout.alignment: Qt.AlignHCenter
                    running: comparisonController.isLoading
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Karşılaştırma hesaplanıyor..."
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }

            // Boş Durum
            ColumnLayout {
                anchors.centerIn: parent
                visible: comparisonController.chartHtml === "" && !comparisonController.isLoading
                spacing: Theme.spaceSm

                ModernIcon {
                    Layout.alignment: Qt.AlignHCenter
                    name: "compare"
                    color: Theme.textMuted
                    size: 40
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.compareEmptyTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Font.DemiBold
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Strings.compareEmptySubtitle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }
    }
}
