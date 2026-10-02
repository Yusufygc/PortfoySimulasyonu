import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    Component.onCompleted: {
        comparisonController.loadAssetOptions()
        comparisonController.runComparison()
    }

    Timer {
        id: debounceTimer
        interval: 300
        repeat: false
        onTriggered: comparisonController.runComparison()
    }

    // Dar pencerede varlık paneli üstte, grafik/metrikler altta (ana sayfa kaydırması devreye girer)
    readonly property bool stacked: width < 960
    readonly property int minContentHeight: stacked ? 1240 : 0

    GridLayout {
        anchors.fill: parent
        columns: root.stacked ? 1 : 2
        columnSpacing: Theme.spaceMd
        rowSpacing: Theme.spaceMd

        // Sol Panel: Varlık Seçim Listesi (300px)
        Rectangle {
            Layout.fillWidth: root.stacked
            Layout.preferredWidth: root.stacked ? -1 : 300
            Layout.minimumWidth: root.stacked ? 0 : 260
            Layout.maximumWidth: root.stacked ? 100000 : 340
            Layout.preferredHeight: root.stacked ? 560 : -1
            Layout.fillHeight: !root.stacked
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceSm

                // Panel Başlığı
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs

                    ModernIcon {
                        name: "layers"
                        color: Theme.accent
                        size: 16
                    }

                    Text {
                        text: Strings.compareAssetsTitle
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.5
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        height: 20
                        width: badgeText.width + 12
                        radius: Theme.radiusXs
                        color: Theme.accentSoft

                        Text {
                            id: badgeText
                            anchors.centerIn: parent
                            text: comparisonController.selectedAssets.length + Strings.compareSelectedSuffix
                            color: Theme.accent
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Varlıklar Listesi
                ListView {
                    id: assetListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: comparisonController.assetOptions

                    ScrollBar.vertical: ModernScrollBar {}

                    delegate: Rectangle {
                        width: assetListView.width
                        height: 38
                        radius: Theme.radiusSm

                        readonly property bool isSelected: comparisonController.selectedAssets.indexOf(modelData.code) !== -1

                        color: isSelected ? Theme.accentSoft : (itemMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                        border.color: isSelected ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spaceSm
                            anchors.rightMargin: Theme.spaceSm
                            spacing: Theme.spaceSm

                            // Seçim Kutucuğu
                            Rectangle {
                                width: 18
                                height: 18
                                radius: 4
                                color: isSelected ? Theme.accent : "transparent"
                                border.color: isSelected ? Theme.accent : Theme.textMuted
                                border.width: 1.5

                                ModernIcon {
                                    anchors.centerIn: parent
                                    name: "check"
                                    color: Theme.textInverse
                                    size: 11
                                    visible: isSelected
                                }
                            }

                            Text {
                                text: modelData.label
                                color: isSelected ? Theme.accent : Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.weight: isSelected ? Font.DemiBold : Font.Normal
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            // Varlık Türü Rozeti
                            Rectangle {
                                height: 18
                                width: kindText.width + 8
                                radius: Theme.radiusXs
                                color: Theme.bgPrimary

                                Text {
                                    id: kindText
                                    anchors.centerIn: parent
                                    text: modelData.kind || "VARLIK"
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 9
                                    font.weight: Font.DemiBold
                                }
                            }
                        }

                        MouseArea {
                            id: itemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                comparisonController.toggleAsset(modelData.code, !isSelected)
                                debounceTimer.restart()
                            }
                        }
                    }
                }

                // Para birimi modu
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs

                    Text {
                        text: Strings.compareCurrencyLabel
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                    }

                    Row {
                        spacing: Theme.spaceXs

                        Repeater {
                            model: [
                                { key: "TL", text: "TL" },
                                { key: "USD", text: "USD" },
                                { key: "REAL", text: Strings.compareCurrencyReal }
                            ]

                            Rectangle {
                                width: Math.max(52, currencyLabel.implicitWidth + 20)
                                height: 28
                                radius: Theme.radiusSm
                                color: comparisonController.currencyMode === modelData.key ? Theme.accent : (currencyMouse.containsMouse ? Theme.bgCardHover : Theme.bgSecondary)
                                border.color: comparisonController.currencyMode === modelData.key ? Theme.accent : Theme.borderSubtle

                                Text {
                                    id: currencyLabel
                                    anchors.centerIn: parent
                                    text: modelData.text
                                    color: comparisonController.currencyMode === modelData.key ? Theme.textInverse : Theme.textSecondary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                    font.weight: Font.DemiBold
                                }

                                MouseArea {
                                    id: currencyMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: comparisonController.setCurrencyMode(modelData.key)
                                }
                            }
                        }
                    }
                }

                // Özel tarih aralığı
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs

                    Text {
                        text: Strings.compareCustomRangeLabel
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.Bold
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        ModernInput {
                            id: txtRangeStart
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            implicitHeight: 30
                            placeholder: "GG.AA.YYYY"
                            text: comparisonController.customStart
                        }

                        ModernInput {
                            id: txtRangeEnd
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            implicitHeight: 30
                            placeholder: "GG.AA.YYYY"
                            text: comparisonController.customEnd
                        }

                        ModernButton {
                            text: Strings.compareBtnApplyRange
                            variant: comparisonController.periodLabel === "ÖZEL" ? "primary" : "secondary"
                            implicitHeight: 30
                            onClicked: comparisonController.setCustomRange(txtRangeStart.text, txtRangeEnd.text)
                        }
                    }
                }

                // Yapay zeka yorumu
                ModernButton {
                    Layout.fillWidth: true
                    text: Strings.compareBtnAi
                    iconName: "ai"
                    variant: "secondary"
                    enabled: comparisonController.metricsList.length > 0
                    onClicked: aiDialog.open()
                }

                // Alt Aksiyon Butonu
                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    radius: Theme.radiusSm
                    color: btnRunMouse.containsMouse ? Theme.accentHover : Theme.accent

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: Theme.spaceXs

                        ModernIcon {
                            name: "refresh"
                            color: Theme.textInverse
                            size: 14
                        }

                        Text {
                            text: Strings.compareBtnRun
                            color: Theme.textInverse
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.weight: Font.DemiBold
                        }
                    }

                    MouseArea {
                        id: btnRunMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            debounceTimer.stop()
                            comparisonController.runComparison()
                        }
                    }
                }
            }
        }

        // Sağ Panel: Grafik + Metrik Tablosu
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 660
            spacing: Theme.spaceMd

            // Performans Grafiği Kartı
            ComparisonChartCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 320
            }

            // Risk-Getiri Metrik Tablosu Kartı
            ComparisonMetricsTable {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                Layout.minimumHeight: 140
            }
        }
    }

    ComparisonAiDialog {
        id: aiDialog
    }

    ToastNotification {
        id: compareToast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        z: 999
    }

    Connections {
        target: comparisonController
        function onOperationResult(success, message) {
            compareToast.show(message, success)
        }
    }
}
