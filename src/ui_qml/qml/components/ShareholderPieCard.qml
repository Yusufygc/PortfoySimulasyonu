import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    implicitWidth: 380
    implicitHeight: 380
    Layout.fillWidth: true
    Layout.minimumHeight: 340
    Layout.preferredHeight: 380

    readonly property var slices: (typeof stock360Controller !== "undefined" && stock360Controller && stock360Controller.shareholderSlices)
                                  ? stock360Controller.shareholderSlices
                                  : []

    readonly property var listData: (typeof stock360Controller !== "undefined" && stock360Controller && stock360Controller.shareholdersList)
                                    ? stock360Controller.shareholdersList
                                    : []

    onSlicesChanged: {
        donutCanvas.requestPaint()
    }

    Connections {
        target: (typeof stock360Controller !== "undefined") ? stock360Controller : null
        function onShareholdersChanged() {
            donutCanvas.requestPaint()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Başlık & Güncelleme
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            RowLayout {
                spacing: 6
                Layout.fillWidth: true

                Rectangle {
                    width: 18
                    height: 18
                    radius: Theme.radiusSm
                    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                    Layout.alignment: Qt.AlignVCenter

                    ModernIcon {
                        anchors.centerIn: parent
                        name: "users"
                        size: 11
                        color: Theme.accent
                    }
                }

                Text {
                    text: Strings.shareholdersTitle
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    font.letterSpacing: 0.5
                }
            }

            // Tarih ve Yenile Butonu
            Text {
                text: stock360Controller ? stock360Controller.shareholderDate : ""
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                visible: text !== ""
            }

            Rectangle {
                width: 26
                height: 26
                radius: Theme.radiusSm
                color: refreshMouse.containsMouse ? Theme.bgCardHover : "transparent"
                border.color: Theme.borderSubtle
                border.width: 1

                ModernIcon {
                    anchors.centerIn: parent
                    name: "refresh"
                    size: 12
                    color: Theme.textMuted
                }

                MouseArea {
                    id: refreshMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (stock360Controller) {
                            stock360Controller.refreshShareholders()
                        }
                    }
                }
            }
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.borderSubtle
        }

        // Orta Gövde: Sol Donut Grafiği, Sağ/Alt Ortak Listesi
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spaceMd

            // Sol: QML Canvas Donut Grafiği
            Item {
                Layout.preferredWidth: 150
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignVCenter

                Canvas {
                    id: donutCanvas
                    anchors.fill: parent
                    antialiasing: true

                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.clearRect(0, 0, width, height);

                        const centerX = width / 2;
                        const centerY = height / 2;
                        const radius = Math.min(centerX, centerY) - 8;
                        const innerRadius = radius * 0.65;

                        if (!root.slices || root.slices.length === 0) {
                            ctx.beginPath();
                            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
                            ctx.arc(centerX, centerY, innerRadius, 2 * Math.PI, 0, true);
                            ctx.fillStyle = Theme.isDark ? "#2a2e39" : "#e6e8ea";
                            ctx.fill();
                            return;
                        }

                        let startAngle = -Math.PI / 2;

                        for (let i = 0; i < root.slices.length; i++) {
                            const slice = root.slices[i];
                            const sliceAngle = (slice.pct || 0) * 2 * Math.PI;
                            const endAngle = startAngle + sliceAngle;

                            ctx.beginPath();
                            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
                            ctx.arc(centerX, centerY, innerRadius, endAngle, startAngle, true);
                            ctx.closePath();

                            ctx.fillStyle = slice.color;
                            ctx.fill();

                            ctx.lineWidth = 1.5;
                            ctx.strokeStyle = Theme.isDark ? "#1e222d" : "#ffffff";
                            ctx.stroke();

                            startAngle = endAngle;
                        }
                    }
                }

                // Donut Ortasındaki Halka Açıklık Oranı
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 0

                    Text {
                        text: stock360Controller ? stock360Controller.freeFloatRatio : "—"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Text {
                        text: Strings.labelFreeFloat
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Sağ: Ortak Listesi (Flickable / ScrollView)
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Flickable {
                    anchors.fill: parent
                    contentHeight: shareholdersCol.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    ColumnLayout {
                        id: shareholdersCol
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: root.listData

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 38
                                radius: Theme.radiusSm
                                color: modelData.isFreeFloat
                                       ? Qt.rgba(Theme.borderSubtle.r, Theme.borderSubtle.g, Theme.borderSubtle.b, 0.2)
                                       : Theme.bgInput
                                border.color: Theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 6

                                    // Renk göstergesi
                                    Rectangle {
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: modelData.color
                                        Layout.alignment: Qt.AlignVCenter
                                    }

                                    // Ortak Adı
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Text {
                                            text: modelData.name
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontXs
                                            font.weight: Font.Medium
                                            color: Theme.textPrimary
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                        Text {
                                            text: modelData.share
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 10
                                            color: Theme.textMuted
                                        }
                                    }

                                    // Pay Oranı
                                    Text {
                                        text: modelData.ratioStr
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSm
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Alt Bilgi: Ödenmiş Sermaye
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Text {
                text: Strings.labelPaidCapital + ":"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }

            Text {
                text: stock360Controller ? stock360Controller.paidCapital : "—"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }
        }

        // Alt Çubuk: KAP Ortaklık Tarihçesi ve Zaman Çizelgesine Geçiş Butonu
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 32
            radius: Theme.radiusSm
            color: Theme.bgInput
            border.color: Theme.borderSubtle
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8

                ModernIcon {
                    name: "history"
                    size: 13
                    color: Theme.accent
                }

                Text {
                    text: Strings.btnOpenShareholderTimeline
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    color: Theme.accent
                }

                Item { Layout.fillWidth: true }

                ModernIcon {
                    name: "arrow-right"
                    size: 11
                    color: Theme.accent
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (typeof stock360Controller !== "undefined" && stock360Controller) {
                        stock360Controller.setViewMode(2)
                    }
                }
            }
        }
    }
}
