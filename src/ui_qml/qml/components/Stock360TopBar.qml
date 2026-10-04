import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse 360 üst araç çubuğu: hisse arama ve hızlı hisse butonları.
ModernCard {
    id: root
    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    Layout.fillWidth: true
    implicitHeight: topBarCol.implicitHeight + Theme.spaceMd * 2

    ColumnLayout {
        id: topBarCol
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Üst Satır: Arama Kutusu ve Aksiyon Butonları
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            // Arama Girişi
            Rectangle {
                Layout.fillWidth: true
                Layout.minimumWidth: 220
                Layout.maximumWidth: 380
                implicitHeight: 36
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: searchInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8

                    ModernIcon {
                        name: "search"
                        size: 14
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignVCenter
                    }

                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textPrimary
                        selectByMouse: true
                        clip: true
                        text: ""

                        Text {
                            text: Strings.searchStockPlaceholder
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textMuted
                            visible: !searchInput.text && !searchInput.activeFocus
                        }

                        onAccepted: {
                            if (text.trim() !== "" && root.ctrl) {
                                root.ctrl.searchTicker(text.trim())
                            }
                        }
                    }

                    Rectangle {
                        visible: searchInput.text !== ""
                        width: 16
                        height: 16
                        radius: 8
                        color: Theme.bgCardHover
                        Layout.alignment: Qt.AlignVCenter

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "close"
                            size: 10
                            color: Theme.textMuted
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: searchInput.text = ""
                        }
                    }
                }
            }

            // Analiz Et Butonu
            ModernButton {
                text: Strings.btnAnalyze
                iconName: "target"
                variant: "primary"
                onClicked: {
                    if (searchInput.text.trim() !== "" && root.ctrl) {
                        root.ctrl.searchTicker(searchInput.text.trim())
                    }
                }
            }

            // Verileri Yenile Butonu
            ModernButton {
                text: Strings.btnRefresh
                iconName: "refresh"
                onClicked: {
                    if (root.ctrl) {
                        root.ctrl.refreshData()
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // TradingView Grafiğinde Aç Butonu
            ModernButton {
                text: Strings.btnOpenInTradingView
                iconName: "linechart"
                onClicked: {
                    if (typeof chartController !== "undefined" && chartController && root.ctrl) {
                        chartController.loadStock(root.ctrl.currentTicker)
                    }
                    if (typeof shellController !== "undefined" && shellController) {
                        shellController.navigateTo(0)
                    }
                }
            }
        }

        // Alt Satır: Hızlı Hisse Seçimi (Flickable)
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Text {
                text: Strings.quickStocksLabel
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
                color: Theme.textMuted
                Layout.alignment: Qt.AlignVCenter
            }

            Flickable {
                Layout.fillWidth: true
                implicitHeight: 28
                contentWidth: pillRow.implicitWidth
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Row {
                    id: pillRow
                    spacing: 6

                    Repeater {
                        model: root.ctrl ? root.ctrl.availableStocks : []

                        Rectangle {
                            id: stockPill
                            property bool isCurrent: (root.ctrl && root.ctrl.currentTicker === modelData)
                            implicitWidth: pillText.implicitWidth + 14
                            implicitHeight: 26
                            radius: Theme.radiusSm
                            color: isCurrent
                            ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2)
                            : (pillMouse.containsMouse ? Theme.bgCardHover : Theme.bgInput)
                            border.color: isCurrent ? Theme.accent : Theme.borderSubtle
                            border.width: 1

                            Behavior on color { ColorAnimation { duration: 120 } }

                            Text {
                                id: pillText
                                anchors.centerIn: parent
                                text: (modelData || "").replace(/\.IS$/i, "")
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: stockPill.isCurrent ? Font.Bold : Font.Normal
                                color: stockPill.isCurrent ? Theme.accent : Theme.textSecondary
                            }

                            MouseArea {
                                id: pillMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (root.ctrl) {
                                        root.ctrl.searchTicker(modelData)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
