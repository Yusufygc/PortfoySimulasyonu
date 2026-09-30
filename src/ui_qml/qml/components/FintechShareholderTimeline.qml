import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null
    property var timelineList: (root.ctrl && root.ctrl.shareholderTimeline) ? root.ctrl.shareholderTimeline : []
    property string filterMode: "all" // "all", "increase", "decrease"
    property string searchQuery: ""

    readonly property var filteredList: {
        if (!timelineList || timelineList.length === 0) return [];
        var q = searchQuery.trim().toLowerCase();
        var res = [];
        for (var i = 0; i < timelineList.length; i++) {
            var item = timelineList[i];
            var isInc = (typeof item.isIncrease !== "undefined") ? item.isIncrease : item.is_increase;
            if (filterMode === "increase" && !isInc) continue;
            if (filterMode === "decrease" && isInc) continue;
            if (q !== "") {
                var name = (item.name || item.holder || "").toLowerCase();
                if (name.indexOf(q) === -1) continue;
            }
            res.push(item);
        }
        return res;
    }

    implicitWidth: 500
    implicitHeight: 560
    Layout.fillWidth: true
    Layout.minimumHeight: 460
    Layout.preferredHeight: 560

    ColumnLayout {
        id: timelineCol
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // 1. Üst Başlık & Olay Sayısı Rozeti
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
                        size: 11
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
                    text: root.filteredList.length + " / " + root.timelineList.length + " " + Strings.labelTotalFilings
                    font.family: Theme.fontMono
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    color: Theme.accent
                }
            }
        }

        // 2. Filtre Butonları & Canlı Arama Kutusu
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            // Filtre Hapları (Tümü / Artışlar / Azalışlar)
            Rectangle {
                implicitHeight: 32
                implicitWidth: filterRow.implicitWidth + 8
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    id: filterRow
                    anchors.centerIn: parent
                    spacing: 4

                    // Sekme: Tümü
                    Rectangle {
                        implicitWidth: filterAllTxt.implicitWidth + 16
                        implicitHeight: 24
                        radius: Theme.radiusSm - 1
                        color: root.filterMode === "all" ? Theme.accent : "transparent"

                        Text {
                            id: filterAllTxt
                            anchors.centerIn: parent
                            text: Strings.filterAllMovements
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: root.filterMode === "all" ? Font.Bold : Font.Normal
                            color: root.filterMode === "all" ? "#ffffff" : Theme.textSecondary
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.filterMode = "all"
                        }
                    }

                    // Sekme: Artışlar (+)
                    Rectangle {
                        implicitWidth: filterIncTxt.implicitWidth + 16
                        implicitHeight: 24
                        radius: Theme.radiusSm - 1
                        color: root.filterMode === "increase" ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.25) : "transparent"

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            ModernIcon {
                                name: "trendingup"
                                size: 10
                                color: root.filterMode === "increase" ? Theme.bullGreen : Theme.textMuted
                            }
                            Text {
                                id: filterIncTxt
                                text: Strings.filterIncreases
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: root.filterMode === "increase" ? Font.Bold : Font.Normal
                                color: root.filterMode === "increase" ? Theme.bullGreen : Theme.textSecondary
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.filterMode = "increase"
                        }
                    }

                    // Sekme: Azalışlar (-)
                    Rectangle {
                        implicitWidth: filterDecTxt.implicitWidth + 16
                        implicitHeight: 24
                        radius: Theme.radiusSm - 1
                        color: root.filterMode === "decrease" ? Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.25) : "transparent"

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            ModernIcon {
                                name: "trendingdown"
                                size: 10
                                color: root.filterMode === "decrease" ? Theme.bearRed : Theme.textMuted
                            }
                            Text {
                                id: filterDecTxt
                                text: Strings.filterDecreases
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: root.filterMode === "decrease" ? Font.Bold : Font.Normal
                                color: root.filterMode === "decrease" ? Theme.bearRed : Theme.textSecondary
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.filterMode = "decrease"
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Hissedar Arama Kutusu
            Rectangle {
                Layout.preferredWidth: 200
                implicitHeight: 32
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: searchInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 6

                    ModernIcon {
                        name: "search"
                        size: 12
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignVCenter
                    }

                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textPrimary
                        selectByMouse: true
                        clip: true
                        text: root.searchQuery
                        onTextChanged: root.searchQuery = text

                        Text {
                            text: Strings.searchShareholderPlaceholder
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                            visible: !searchInput.text && !searchInput.activeFocus
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }

                    Rectangle {
                        visible: searchInput.text !== ""
                        width: 16
                        height: 16
                        radius: 8
                        color: Theme.isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)"
                        Layout.alignment: Qt.AlignVCenter

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "close"
                            size: 8
                            color: Theme.textMuted
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                searchInput.text = "";
                                root.searchQuery = "";
                            }
                        }
                    }
                }
            }
        }

        // Ayırıcı
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // 3. İçerik Alanı: Boş Durum veya Zaman Çizelgesi Akışı
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Boş Durum
            Item {
                visible: root.filteredList.length === 0
                anchors.fill: parent

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 8

                    Rectangle {
                        width: 42
                        height: 42
                        radius: 21
                        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12)
                        Layout.alignment: Qt.AlignHCenter

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "history"
                            size: 18
                            color: Theme.accent
                        }
                    }

                    Text {
                        text: Strings.emptyTimelineSearch
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Text {
                        text: Strings.emptyTimelineSearchSubtitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Zaman Çizelgesi Akışı (Flickable + ModernScrollBar)
            Flickable {
                id: timelineFlick
                visible: root.filteredList.length > 0
                anchors.fill: parent
                contentHeight: timelineItemsCol.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ModernScrollBar {
                    parent: timelineFlick
                    anchors.right: timelineFlick.right
                    anchors.top: timelineFlick.top
                    anchors.bottom: timelineFlick.bottom
                }

                ColumnLayout {
                    id: timelineItemsCol
                    width: Math.max(100, timelineFlick.width - 12)
                    spacing: 6

                    Repeater {
                        model: root.filteredList

                        Item {
                            id: timelineItem
                            Layout.fillWidth: true
                            implicitHeight: 66

                            // Dikey Çizgi (Zaman çizgisi ekseni)
                            Rectangle {
                                anchors.left: parent.left
                                anchors.leftMargin: 19
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                width: 2
                                color: Theme.borderSubtle
                                visible: index < root.filteredList.length - 1
                            }

                            // Zaman Çizgisi Noktası (Node)
                            Rectangle {
                                id: nodeDot
                                anchors.left: parent.left
                                anchors.leftMargin: 13
                                anchors.verticalCenter: parent.verticalCenter
                                width: 14
                                height: 14
                                radius: 7
                                property bool isInc: (typeof modelData.isIncrease !== "undefined") ? modelData.isIncrease : modelData.is_increase
                                color: Theme.bgCard
                                border.color: isInc ? Theme.bullGreen : Theme.bearRed
                                border.width: 2

                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 6
                                    height: 6
                                    radius: 3
                                    color: nodeDot.isInc ? Theme.bullGreen : Theme.bearRed
                                }
                            }

                            // Genişletilmiş Olay Kartı
                            Rectangle {
                                anchors.left: nodeDot.right
                                anchors.leftMargin: 14
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                height: 60
                                radius: Theme.radiusSm
                                color: itemMouse.containsMouse ? Theme.bgCardHover : Theme.bgInput
                                border.color: itemMouse.containsMouse ? Theme.borderFocus : Theme.borderSubtle
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    anchors.topMargin: 8
                                    anchors.bottomMargin: 8
                                    spacing: 4

                                    // Üst Satır: Tarih Rozeti + Hissedar Adı + Net Değişim Rozeti
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        // Tarih Rozeti
                                        Rectangle {
                                            implicitWidth: dTxt.implicitWidth + 10
                                            implicitHeight: 20
                                            radius: 4
                                            color: Theme.isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)"
                                            Layout.alignment: Qt.AlignVCenter

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
                                            font.weight: Font.Bold
                                            color: Theme.textPrimary
                                            elide: Text.ElideRight
                                            Layout.alignment: Qt.AlignVCenter
                                        }

                                        // Değişim Rozeti (Yeşil veya Kırmızı)
                                        Rectangle {
                                            property bool isInc: (typeof modelData.isIncrease !== "undefined") ? modelData.isIncrease : modelData.is_increase
                                            implicitWidth: diffTxt.implicitWidth + diffRow.spacing + 16
                                            implicitHeight: 22
                                            radius: 11
                                            color: isInc
                                                   ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.15)
                                                   : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.15)
                                            border.color: isInc
                                                   ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.3)
                                                   : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.3)
                                            border.width: 1
                                            Layout.alignment: Qt.AlignVCenter

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

                                    // Alt Satır: Önceki -> Yeni Pay + Oy Hakkı + Oran Karşılaştırma Çubuğu
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        // Oran Geçiş Rozeti
                                        Rectangle {
                                            implicitWidth: ratioTransitionTxt.implicitWidth + 10
                                            implicitHeight: 18
                                            radius: 3
                                            color: Theme.isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.04)"
                                            Layout.alignment: Qt.AlignVCenter

                                            Text {
                                                id: ratioTransitionTxt
                                                anchors.centerIn: parent
                                                text: (modelData.oldRatio && modelData.newRatio)
                                                      ? (modelData.oldRatio + "  ->  " + modelData.newRatio)
                                                      : ("%" + (modelData.old_pct ? modelData.old_pct.toFixed(2) : "0.00") + "  ->  %" + (modelData.new_pct ? modelData.new_pct.toFixed(2) : "0.00"))
                                                font.family: Theme.fontMono
                                                font.pixelSize: 10
                                                font.weight: Font.Medium
                                                color: Theme.textSecondary
                                            }
                                        }

                                        // Oy Hakkı Rozeti
                                        Rectangle {
                                            visible: !!modelData.votingRatio
                                            implicitWidth: votingRightTxt.implicitWidth + 8
                                            implicitHeight: 18
                                            radius: 3
                                            color: Theme.isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.04)"
                                            Layout.alignment: Qt.AlignVCenter

                                            Text {
                                                id: votingRightTxt
                                                anchors.centerIn: parent
                                                text: Strings.labelVotingRatio + ": " + (modelData.votingRatio || "—")
                                                font.family: Theme.fontMono
                                                font.pixelSize: 9
                                                color: Theme.textMuted
                                            }
                                        }

                                        Item { Layout.fillWidth: true }

                                        // Mini Oran Seviye Çubuğu
                                        RowLayout {
                                            spacing: 6
                                            Layout.alignment: Qt.AlignVCenter

                                            Text {
                                                text: Strings.labelCapitalShare + ":"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: 9
                                                color: Theme.textMuted
                                            }

                                            Rectangle {
                                                width: 60
                                                height: 5
                                                radius: 2.5
                                                color: Theme.borderSubtle

                                                Rectangle {
                                                    anchors.left: parent.left
                                                    anchors.top: parent.top
                                                    anchors.bottom: parent.bottom
                                                    radius: 2.5
                                                    property real ratioVal: {
                                                        var s = modelData.newRatio || "";
                                                        var num = parseFloat(s.replace("%", "").replace(",", "."));
                                                        return isNaN(num) ? 0.0 : Math.min(1.0, Math.max(0.0, num / 100.0));
                                                    }
                                                    width: Math.max(3, parent.width * ratioVal)
                                                    color: (typeof modelData.isIncrease !== "undefined" && modelData.isIncrease)
                                                           ? Theme.bullGreen
                                                           : Theme.accent
                                                }
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
    }
}
