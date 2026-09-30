import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

ModernCard {
    id: root

    readonly property var ctrl: (typeof stock360Controller !== "undefined") ? stock360Controller : null

    implicitHeight: Math.max(520, tableColumn.implicitHeight + Theme.spaceMd * 2)
    Layout.fillWidth: true

    ColumnLayout {
        id: tableColumn
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // -----------------------------------------------------------------
        // 1. ÜST KONTROL ÇUBUĞU (Tab Seçici + Canlı Arama + Dönem Kapsülleri)
        // -----------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            // 3'lü Segment Seçici: [Bilanço] | [Gelir Tablosu] | [Nakit Akışı]
            Rectangle {
                implicitHeight: 34
                implicitWidth: segmentRow.implicitWidth + 8
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    id: segmentRow
                    anchors.centerIn: parent
                    spacing: 4

                    // Bilanço Tabı
                    Rectangle {
                        implicitWidth: bTxt.implicitWidth + 16
                        implicitHeight: 28
                        radius: Theme.radiusSm - 1
                        property bool isCurrent: (root.ctrl && root.ctrl.statementType === "bilanco")
                        color: isCurrent ? Theme.accent : "transparent"

                        Text {
                            id: bTxt
                            anchors.centerIn: parent
                            text: Strings.tabBalanceSheet
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: parent.isCurrent ? Font.Bold : Font.Normal
                            color: parent.isCurrent ? "#ffffff" : Theme.textSecondary
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (root.ctrl) root.ctrl.setStatementType("bilanco")
                        }
                    }

                    // Gelir Tablosu Tabı
                    Rectangle {
                        implicitWidth: gTxt.implicitWidth + 16
                        implicitHeight: 28
                        radius: Theme.radiusSm - 1
                        property bool isCurrent: (root.ctrl && root.ctrl.statementType === "gelir")
                        color: isCurrent ? Theme.accent : "transparent"

                        Text {
                            id: gTxt
                            anchors.centerIn: parent
                            text: Strings.tabIncomeStatement
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: parent.isCurrent ? Font.Bold : Font.Normal
                            color: parent.isCurrent ? "#ffffff" : Theme.textSecondary
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (root.ctrl) root.ctrl.setStatementType("gelir")
                        }
                    }

                    // Nakit Akış Tablosu Tabı
                    Rectangle {
                        implicitWidth: nTxt.implicitWidth + 16
                        implicitHeight: 28
                        radius: Theme.radiusSm - 1
                        property bool isCurrent: (root.ctrl && root.ctrl.statementType === "nakit_akim")
                        color: isCurrent ? Theme.accent : "transparent"

                        Text {
                            id: nTxt
                            anchors.centerIn: parent
                            text: Strings.tabCashFlowStatement
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: parent.isCurrent ? Font.Bold : Font.Normal
                            color: parent.isCurrent ? "#ffffff" : Theme.textSecondary
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (root.ctrl) root.ctrl.setStatementType("nakit_akim")
                        }
                    }
                }
            }

            // Canlı Arama Kutusu
            Rectangle {
                Layout.fillWidth: true
                Layout.minimumWidth: 200
                Layout.maximumWidth: 340
                implicitHeight: 34
                radius: Theme.radiusSm
                color: Theme.bgInput
                border.color: searchField.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 8
                    spacing: 6

                    ModernIcon {
                        name: "search"
                        size: 13
                        color: Theme.textMuted
                        Layout.alignment: Qt.AlignVCenter
                    }

                    TextInput {
                        id: searchField
                        Layout.fillWidth: true
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                        color: Theme.textPrimary
                        selectByMouse: true
                        clip: true
                        text: root.ctrl ? root.ctrl.statementSearchQuery : ""

                        Text {
                            text: Strings.searchStatementPlaceholder
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                            visible: !searchField.text && !searchField.activeFocus
                        }

                        onTextEdited: {
                            if (root.ctrl) root.ctrl.setStatementSearchQuery(searchField.text.trim())
                        }
                    }

                    // Arama Temizle Butonu
                    Rectangle {
                        visible: searchField.text !== ""
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
                            onClicked: {
                                searchField.text = ""
                                if (root.ctrl) root.ctrl.setStatementSearchQuery("")
                            }
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Dönem Seçici Kapsüller (4, 8, 12, Tüm Geçmiş)
            RowLayout {
                spacing: 4

                Repeater {
                    model: [
                        { label: Strings.period4Quarters, val: 4 },
                        { label: Strings.period8Quarters, val: 8 },
                        { label: Strings.period12Quarters, val: 12 },
                        { label: Strings.periodAllQuarters, val: 0 }
                    ]

                    Rectangle {
                        required property var modelData
                        implicitWidth: pCapTxt.implicitWidth + 14
                        implicitHeight: 28
                        radius: Theme.radiusSm
                        property bool isSel: (root.ctrl && root.ctrl.periodsCount === modelData.val)
                        color: isSel ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18) : Theme.bgInput
                        border.color: isSel ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        Text {
                            id: pCapTxt
                            anchors.centerIn: parent
                            text: modelData.label
                            font.family: Theme.fontFamily
                            font.pixelSize: 11
                            font.weight: parent.isSel ? Font.Bold : Font.Normal
                            color: parent.isSel ? Theme.accent : Theme.textSecondary
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.ctrl) root.ctrl.setFinancialsPeriods(modelData.val)
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

        // -----------------------------------------------------------------
        // 2. FİNANSAL TABLO (Yatay Kaydırılabilir Tablo Gövdesi)
        // -----------------------------------------------------------------
        Rectangle {
            id: tableContainer
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(600, Math.max(380, rowsRepeater.count * 32 + 40))
            color: Theme.bgCard
            radius: Theme.radiusSm
            clip: true

            property var periods: (root.ctrl && root.ctrl.activeStatementPeriods) ? root.ctrl.activeStatementPeriods : []
            property real colLabelWidth: 260
            property real colPeriodWidth: 115
            property real colYoyWidth: 120
            property real totalTableWidth: Math.max(tableContainer.width, colLabelWidth + periods.length * colPeriodWidth + colYoyWidth)

            Flickable {
                id: hFlickable
                anchors.fill: parent
                contentWidth: tableContainer.totalTableWidth
                contentHeight: tableContentCol.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                ColumnLayout {
                    id: tableContentCol
                    width: tableContainer.totalTableWidth
                    spacing: 1

                    // TABLO BAŞLIK SATIRI (HEADER)
                    Rectangle {
                        width: tableContainer.totalTableWidth
                        height: 34
                        color: Theme.bgInput
                        border.color: Theme.borderSubtle
                        border.width: 1

                        Row {
                            anchors.fill: parent

                            // Kalem Adı Başlığı
                            Item {
                                width: tableContainer.colLabelWidth
                                height: parent.height

                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: Strings.thStatementItem
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    color: Theme.textMuted
                                }
                            }

                            // Dönem Başlıkları (2024/09, 2024/06...)
                            Repeater {
                                model: tableContainer.periods

                                Item {
                                    width: tableContainer.colPeriodWidth
                                    height: parent.height

                                    Text {
                                        anchors.right: parent.right
                                        anchors.rightMargin: 12
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData
                                        font.family: Theme.fontMono
                                        font.pixelSize: 11
                                        font.weight: Font.Bold
                                        color: Theme.textPrimary
                                    }
                                }
                            }

                            // Yıllık Değişim (YoY)
                            Item {
                                width: tableContainer.colYoyWidth
                                height: parent.height

                                Text {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: Strings.thYoYChange
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    color: Theme.textMuted
                                }
                            }
                        }
                    }

                    // TABLO SATIRLARI (DATA ROWS)
                    Repeater {
                        id: rowsRepeater
                        model: (root.ctrl && root.ctrl.financialTableRows) ? root.ctrl.financialTableRows : []

                        Rectangle {
                            id: rowRect
                            width: tableContainer.totalTableWidth
                            height: rowRect.isHdr ? 34 : 30
                            property bool isHdr: Boolean(modelData && (modelData.isHeader || modelData.is_header))
                            property bool hasChg: Boolean(modelData && ((modelData.yoyChange && modelData.yoyChange !== "—") || modelData.has_change))
                            property bool isPosYoy: Boolean(modelData && (modelData.isPositiveYoY || modelData.is_positive))

                            color: isHdr
                                   ? (Theme.isDark ? "rgba(59, 130, 246, 0.12)" : "rgba(37, 99, 235, 0.08)")
                                   : (rowMouse.containsMouse ? Theme.bgCardHover : "transparent")

                            border.color: isHdr ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2) : "transparent"
                            border.width: isHdr ? 1 : 0

                            Row {
                                anchors.fill: parent

                                // Kalem Adı Hücresi
                                Item {
                                    width: tableContainer.colLabelWidth
                                    height: parent.height

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: rowRect.isHdr ? 10 : 20
                                        spacing: 6

                                        Rectangle {
                                            visible: rowRect.isHdr
                                            width: 4
                                            height: 14
                                            radius: 2
                                            color: Theme.accent
                                            Layout.alignment: Qt.AlignVCenter
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: (modelData && (modelData.name || modelData.label)) ? ("" + (modelData.name || modelData.label)) : ""
                                            font.family: Theme.fontFamily
                                            font.pixelSize: rowRect.isHdr ? 11 : Theme.fontXs
                                            font.weight: rowRect.isHdr ? Font.Bold : Font.Normal
                                            color: rowRect.isHdr ? Theme.accent : Theme.textPrimary
                                            elide: Text.ElideRight
                                        }
                                    }
                                }

                                // Dönem Değer Hücreleri
                                Repeater {
                                    model: (modelData && modelData.values) ? modelData.values : []

                                    Item {
                                        width: tableContainer.colPeriodWidth
                                        height: parent.height

                                        Text {
                                            anchors.right: parent.right
                                            anchors.rightMargin: 12
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: (typeof modelData !== "undefined" && modelData !== null) ? ("" + modelData) : "—"
                                            font.family: Theme.fontMono
                                            font.pixelSize: 11
                                            font.weight: rowRect.isHdr ? Font.Bold : Font.Normal
                                            color: rowRect.isHdr ? Theme.textPrimary : Theme.textSecondary
                                        }
                                    }
                                }

                                // YoY Değişim Hücresi
                                Item {
                                    width: tableContainer.colYoyWidth
                                    height: parent.height

                                    // YoY Rozeti
                                    Rectangle {
                                        visible: rowRect.hasChg
                                        anchors.right: parent.right
                                        anchors.rightMargin: 12
                                        anchors.verticalCenter: parent.verticalCenter
                                        implicitWidth: yoyTxt.implicitWidth + 10
                                        implicitHeight: 20
                                        radius: 10
                                        color: rowRect.isPosYoy
                                               ? Qt.rgba(Theme.bullGreen.r, Theme.bullGreen.g, Theme.bullGreen.b, 0.15)
                                               : Qt.rgba(Theme.bearRed.r, Theme.bearRed.g, Theme.bearRed.b, 0.15)

                                        Text {
                                            id: yoyTxt
                                            anchors.centerIn: parent
                                            text: (modelData && (modelData.yoyChange || modelData.yoy)) ? ("" + (modelData.yoyChange || modelData.yoy)) : ""
                                            font.family: Theme.fontMono
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                            color: rowRect.isPosYoy ? Theme.bullGreen : Theme.bearRed
                                        }
                                    }

                                    Text {
                                        visible: !rowRect.hasChg
                                        anchors.right: parent.right
                                        anchors.rightMargin: 16
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "—"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 11
                                        color: Theme.textMuted
                                    }
                                }
                            }

                            // Alt İnce Çizgi
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 1
                                color: Theme.isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.04)"
                            }

                            MouseArea {
                                id: rowMouse
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
