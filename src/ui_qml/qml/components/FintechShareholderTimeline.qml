import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    property var timelineList: (root.ctrl && root.ctrl.shareholderTimeline) ? root.ctrl.shareholderTimeline : []

    implicitHeight: Math.max(340, timelineCol.implicitHeight + Theme.spaceMd * 2)
    Layout.fillWidth: true

    ColumnLayout {
        id: timelineCol
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Üst Başlık & Olay Sayısı Rozeti
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            RowLayout {
                spacing: 6
                Layout.fillWidth: true

                Rectangle {
                    width: 20
                    height: 20
                    radius: Theme.radiusSm
                    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                    Layout.alignment: Qt.AlignVCenter

                    ModernIcon {
                        anchors.centerIn: parent
                        name: "history"
                        size: 12
                        color: Theme.accent
                    }
                }

                Text {
                    text: Strings.timelineTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    font.letterSpacing: 0.5
                }
            }

            // Olay Sayısı Rozeti
            Rectangle {
                implicitWidth: countTxt.implicitWidth + 14
                implicitHeight: 22
                radius: 11
                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.3)
                border.width: 1

                Text {
                    id: countTxt
                    anchors.centerIn: parent
                    text: root.timelineList.length + " Pay Değişim Hareketi"
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    color: Theme.accent
                }
            }
        }

        // Ayırıcı
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // Boş Durum
        Item {
            visible: root.timelineList.length === 0
            Layout.fillWidth: true
            implicitHeight: 120

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 6

                ModernIcon {
                    name: "users"
                    size: 24
                    color: Theme.textMuted
                    Layout.alignment: Qt.AlignHCenter
                }

                Text {
                    text: "Son dönemde önemli pay değişim bildirimi bulunamadı."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Dikey Zaman Çizelgesi Akışı (Timeline List)
        ColumnLayout {
            visible: root.timelineList.length > 0
            Layout.fillWidth: true
            spacing: 0

            Repeater {
                model: root.timelineList

                Item {
                    id: timelineItem
                    Layout.fillWidth: true
                    implicitHeight: 54

                    // Dikey Çizgi (Zaman çizgisi ekseni)
                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 19
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 2
                        color: Theme.borderSubtle
                        visible: index < root.timelineList.length - 1
                    }

                    // Zaman Çizgisi Noktası (Node)
                    Rectangle {
                        id: nodeDot
                        anchors.left: parent.left
                        anchors.leftMargin: 15
                        anchors.verticalCenter: parent.verticalCenter
                        width: 10
                        height: 10
                        radius: 5
                        property bool isInc: (typeof modelData.isIncrease !== "undefined") ? modelData.isIncrease : modelData.is_increase
                        color: isInc ? Theme.bullGreen : Theme.bearRed
                        border.color: Theme.bgCard
                        border.width: 2
                    }

                    // Kart İçeriği
                    Rectangle {
                        anchors.left: nodeDot.right
                        anchors.leftMargin: 16
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: 44
                        radius: Theme.radiusSm
                        color: itemMouse.containsMouse ? Theme.bgCardHover : Theme.bgInput
                        border.color: Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 12

                            // Tarih Rozeti
                            Rectangle {
                                implicitWidth: dTxt.implicitWidth + 12
                                implicitHeight: 22
                                radius: 4
                                color: Theme.isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)"

                                Text {
                                    id: dTxt
                                    anchors.centerIn: parent
                                    text: modelData.date || "—"
                                    font.family: Theme.fontMono
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                    color: Theme.textSecondary
                                }
                            }

                            // Hissedar Adı
                            Text {
                                Layout.fillWidth: true
                                text: modelData.name || modelData.holder || ""
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                            }

                            // Önceki ➔ Yeni Pay
                            Text {
                                text: (modelData.oldRatio && modelData.newRatio)
                                      ? (modelData.oldRatio + " → " + modelData.newRatio)
                                      : ("%" + (modelData.old_pct ? modelData.old_pct.toFixed(2) : "0.00") + " → %" + (modelData.new_pct ? modelData.new_pct.toFixed(2) : "0.00"))
                                font.family: Theme.fontMono
                                font.pixelSize: 11
                                color: Theme.textMuted
                            }

                            // Değişim Rozeti (Yeşil veya Kırmızı)
                            Rectangle {
                                property bool isInc: (typeof modelData.isIncrease !== "undefined") ? modelData.isIncrease : modelData.is_increase
                                implicitWidth: diffTxt.implicitWidth + diffRow.spacing + 18
                                implicitHeight: 22
                                radius: 11
                                color: isInc
                                       ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.15)
                                       : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.15)

                                RowLayout {
                                    id: diffRow
                                    anchors.centerIn: parent
                                    spacing: 4

                                    ModernIcon {
                                        name: parent.parent.isInc ? "trendingup" : "trendingdown"
                                        size: 11
                                        color: parent.parent.isInc ? Theme.bullGreen : Theme.bearRed
                                    }

                                    Text {
                                        id: diffTxt
                                        text: modelData.diffStr || modelData.diff_str || ""
                                        font.family: Theme.fontMono
                                        font.pixelSize: 10
                                        font.weight: Font.Bold
                                        color: parent.parent.isInc ? Theme.bullGreen : Theme.bearRed
                                    }
                                }
                            }
                        }

                        MouseArea {
                            id: itemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                        }
                    }
                }
            }
        }
    }
}
