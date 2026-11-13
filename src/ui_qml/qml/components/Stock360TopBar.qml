import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse 360 üst araç çubuğu: hisse arama ve aksiyon butonları.
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
    }
}
