import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Hisse 360 şirket bilgisi ve fiyat hero kartı (her görünüm modunda görünür).
ModernCard {
    id: root
    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    Layout.fillWidth: true
    implicitHeight: heroCol.implicitHeight + Theme.spaceMd * 2

    ColumnLayout {
        id: heroCol
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            // Sol: Sembol & Şirket Adı & Sektör
            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true

                RowLayout {
                    spacing: Theme.spaceSm

                    Text {
                        text: root.ctrl ? (root.ctrl.currentTicker || "—").replace(/\.IS$/i, "") : "—"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }

                    Rectangle {
                        implicitWidth: sectorBadgeText.implicitWidth + 12
                        implicitHeight: 20
                        radius: Theme.radiusSm
                        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12)
                        border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.25)
                        border.width: 1
                        Layout.alignment: Qt.AlignVCenter

                        Text {
                            id: sectorBadgeText
                            anchors.centerIn: parent
                            text: root.ctrl ? root.ctrl.sector : "—"
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            color: Theme.accent
                        }
                    }
                }

                Text {
                    text: root.ctrl ? root.ctrl.companyName : "—"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                    Layout.maximumWidth: 400
                }
            }

            Item { Layout.fillWidth: true }

            // Sağ: Canlı / Son Fiyat ve Günlük Değişim
            ColumnLayout {
                spacing: 2
                Layout.alignment: Qt.AlignRight

                RowLayout {
                    spacing: 8
                    Layout.alignment: Qt.AlignRight

                    Text {
                        text: root.ctrl ? root.ctrl.lastPrice : "₺0.00"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }

                    Rectangle {
                        implicitWidth: changeRow.implicitWidth + 12
                        implicitHeight: 24
                        radius: Theme.radiusSm
                        color: (root.ctrl && root.ctrl.isDailyPositive)
                        ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.15)
                        : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.15)
                        border.color: (root.ctrl && root.ctrl.isDailyPositive)
                        ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.3)
                        : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.3)
                        border.width: 1
                        Layout.alignment: Qt.AlignVCenter

                        RowLayout {
                            id: changeRow
                            anchors.centerIn: parent
                            spacing: 4

                            ModernIcon {
                                name: (root.ctrl && root.ctrl.isDailyPositive)
                                ? "trendingup"
                                : "trendingdown"
                                size: 12
                                color: (root.ctrl && root.ctrl.isDailyPositive)
                                ? Theme.bullGreen
                                : Theme.bearRed
                            }

                            Text {
                                text: root.ctrl ? root.ctrl.dailyChange : "%0.00"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.Bold
                                color: (root.ctrl && root.ctrl.isDailyPositive)
                                ? Theme.bullGreen
                                : Theme.bearRed
                            }
                        }
                    }
                }

                // 52 Haftalık Aralık Çubuğu
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    spacing: 2

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: Strings.stock360Low52Prefix + (root.ctrl ? root.ctrl.week52Low : "—")
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: Strings.stock360High52Prefix + (root.ctrl ? root.ctrl.week52High : "—")
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textMuted
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 5
                        radius: 2.5
                        color: Theme.bgInput

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: Math.max(8, parent.width * (root.ctrl ? root.ctrl.week52RangePct : 0.5))
                            radius: 2.5
                            color: Theme.accent
                        }
                    }
                }
            }
        }
    }
}
