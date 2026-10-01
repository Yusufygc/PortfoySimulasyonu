import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spaceMd

        // 1. Üst Kontrol Barı: Ay Seçici & Kaydet
        Rectangle {
            Layout.fillWidth: true
            height: 56
            color: Theme.bgCard
            radius: Theme.radiusMd
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.spaceMd
                anchors.rightMargin: Theme.spaceMd
                spacing: Theme.spaceMd

                ModernIcon {
                    name: "calendar"
                    color: Theme.accent
                    size: 18
                }

                Text {
                    text: Strings.budgetMonthLabel + ":"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                }

                ComboBox {
                    id: comboMonth
                    Layout.preferredWidth: 130
                    Layout.preferredHeight: 34
                    model: planningController.availableMonths

                    currentIndex: {
                        var idx = planningController.availableMonths.indexOf(planningController.currentMonth)
                        return idx >= 0 ? idx : 0
                    }

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: comboMonth.hovered ? Theme.accent : Theme.borderSubtle
                        border.width: 1
                    }

                    contentItem: Text {
                        leftPadding: Theme.spaceSm
                        rightPadding: 24
                        text: comboMonth.displayText
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    indicator: ModernIcon {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        name: "chevrondown"
                        size: 12
                        color: Theme.textMuted
                    }

                    popup: Popup {
                        y: comboMonth.height + 2
                        width: Math.max(comboMonth.width, 140)
                        implicitHeight: Math.min(260, contentItem.implicitHeight + 8)
                        padding: 4

                        contentItem: ListView {
                            clip: true
                            implicitHeight: contentHeight
                            model: comboMonth.popup.visible ? comboMonth.delegateModel : null
                            currentIndex: comboMonth.highlightedIndex

                            ScrollBar.vertical: ModernScrollBar {}
                        }

                        background: Rectangle {
                            color: Theme.bgCard
                            border.color: Theme.borderCard
                            border.width: 1
                            radius: Theme.radiusSm
                        }
                    }

                    delegate: ItemDelegate {
                        width: comboMonth.width
                        height: 30
                        highlighted: comboMonth.highlightedIndex === index

                        contentItem: Text {
                            text: modelData
                            color: highlighted ? Theme.accent : Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            verticalAlignment: Text.AlignVCenter
                        }

                        background: Rectangle {
                            color: highlighted ? Theme.accentSoft : (hovered ? Theme.bgCardHover : "transparent")
                            radius: Theme.radiusXs
                        }
                    }

                    onActivated: function(idx) {
                        var selMonth = planningController.availableMonths[idx]
                        if (selMonth) {
                            planningController.loadBudgetForMonth(selMonth)
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: Strings.budgetKpiTarget + " (₺):"
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }

                TextField {
                    id: txtTarget
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 34
                    text: planningController.savingsTarget > 0 ? planningController.savingsTarget.toString() : ""
                    placeholderText: "0"
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    leftPadding: Theme.spaceSm
                    rightPadding: Theme.spaceSm
                    inputMethodHints: Qt.ImhFormattedNumbersOnly

                    background: Rectangle {
                        color: Theme.bgInput
                        radius: Theme.radiusSm
                        border.color: txtTarget.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                        border.width: 1
                    }
                }

                Rectangle {
                    width: 130
                    height: 34
                    radius: Theme.radiusSm
                    color: btnSaveMouse.containsMouse ? Theme.accentHover : Theme.accent

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: Theme.spaceXs

                        ModernIcon {
                            name: "check"
                            color: Theme.textInverse
                            size: 14
                        }

                        Text {
                            text: Strings.budgetBtnSave
                            color: Theme.textInverse
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                        }
                    }

                    MouseArea {
                        id: btnSaveMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            var t = parseFloat(txtTarget.text.replace(",", ".")) || 0.0
                            planningController.saveCurrentBudget(t)
                        }
                    }
                }
            }
        }

        // 2. KPI Kartları
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            // Toplam Gelir
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
                            name: "trendingup"
                            color: Theme.bullGreen
                            size: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.budgetKpiIncome
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                        Text {
                            text: planningController.totalIncomeFormatted
                            color: Theme.bullGreen
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                    }
                }
            }

            // Toplam Gider
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
                        color: Theme.bearRedSoft

                        ModernIcon {
                            anchors.centerIn: parent
                            name: "trendingdown"
                            color: Theme.bearRed
                            size: 18
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: Strings.budgetKpiExpense
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                        Text {
                            text: planningController.totalExpenseFormatted
                            color: Theme.bearRed
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                    }
                }
            }

            // Net Tasarruf Gücü
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
                            text: Strings.budgetKpiSavings
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                        }
                        Text {
                            text: planningController.netSavingsPotentialFormatted
                            color: planningController.netSavingsPotential >= 0 ? Theme.textPrimary : Theme.bearRed
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLg
                            font.weight: Font.Bold
                        }
                    }
                }
            }
        }

        // 3. İki Sütunlu Kalemler Alanı (Gelirler - Giderler)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spaceMd

            // Sol Sütun: Gelir Kalemleri
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

                    // Başlık
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        ModernIcon {
                            name: "plus"
                            color: Theme.bullGreen
                            size: 16
                        }

                        Text {
                            text: Strings.budgetIncomeTitle
                            color: Theme.bullGreen
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }

                        Text {
                            text: planningController.incomeItems.length + " kalem"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                        }
                    }

                    // Hızlı Ekleme Çubuğu
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        TextField {
                            id: txtIncName
                            Layout.fillWidth: true
                            placeholderText: "Maaş / Ek Gelir"
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm

                            background: Rectangle {
                                color: Theme.bgInput
                                radius: Theme.radiusSm
                                border.color: Theme.borderSubtle
                                border.width: 1
                            }
                        }

                        TextField {
                            id: txtIncAmount
                            Layout.preferredWidth: 90
                            placeholderText: "Tutar"
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            inputMethodHints: Qt.ImhFormattedNumbersOnly

                            background: Rectangle {
                                color: Theme.bgInput
                                radius: Theme.radiusSm
                                border.color: Theme.borderSubtle
                                border.width: 1
                            }
                        }

                        Rectangle {
                            width: 32
                            height: 32
                            radius: Theme.radiusSm
                            color: Theme.bullGreen

                            ModernIcon {
                                anchors.centerIn: parent
                                name: "plus"
                                color: Theme.textInverse
                                size: 14
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var amt = parseFloat(txtIncAmount.text.replace(",", "."))
                                    if (txtIncName.text.trim() && !isNaN(amt) && amt > 0) {
                                        planningController.addBudgetItem("INCOME", txtIncName.text.trim(), amt)
                                        txtIncName.text = ""
                                        txtIncAmount.text = ""
                                    }
                                }
                            }
                        }
                    }

                    // Liste
                    ListView {
                        id: incListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: planningController.incomeItems

                        ScrollBar.vertical: ModernScrollBar {}

                        delegate: Rectangle {
                            width: incListView.width
                            height: 38
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceSm
                                anchors.rightMargin: Theme.spaceSm
                                spacing: Theme.spaceSm

                                Text {
                                    text: modelData.name
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: modelData.amountFormatted
                                    color: Theme.bullGreen
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }

                                // Pin Butonu (Sabitleme)
                                Rectangle {
                                    width: 24
                                    height: 24
                                    radius: Theme.radiusXs
                                    color: modelData.isPinned ? Theme.accentSoft : (btnPinIncMouse.containsMouse ? Theme.bgCardHover : "transparent")
                                    border.color: modelData.isPinned ? Theme.accent : "transparent"
                                    border.width: 1

                                    ModernIcon {
                                        anchors.centerIn: parent
                                        name: "bookmark"
                                        color: modelData.isPinned ? Theme.accent : (btnPinIncMouse.containsMouse ? Theme.textPrimary : Theme.textMuted)
                                        size: 13
                                    }

                                    ToolTip.visible: btnPinIncMouse.containsMouse
                                    ToolTip.text: modelData.isPinned ? "Sabitlendi (Her ay otomatik gelir) - Kaldırmak için tıkla" : "Bu kalemi sabitle (Gelecek aylara aktar)"
                                    ToolTip.delay: 300

                                    MouseArea {
                                        id: btnPinIncMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: planningController.togglePinItem("INCOME", modelData.name, modelData.amount, !modelData.isPinned)
                                    }
                                }

                                Rectangle {
                                    width: 24
                                    height: 24
                                    radius: Theme.radiusXs
                                    color: btnDelIncMouse.containsMouse ? Theme.bearRedSoft : "transparent"

                                    ModernIcon {
                                        anchors.centerIn: parent
                                        name: "trash"
                                        color: btnDelIncMouse.containsMouse ? Theme.bearRed : Theme.textMuted
                                        size: 12
                                    }

                                    MouseArea {
                                        id: btnDelIncMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: planningController.removeBudgetItem("INCOME", index)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Sağ Sütun: Gider Kalemleri
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

                    // Başlık
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        ModernIcon {
                            name: "trendingdown"
                            color: Theme.bearRed
                            size: 16
                        }

                        Text {
                            text: Strings.budgetExpenseTitle
                            color: Theme.bearRed
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }

                        Text {
                            text: planningController.expenseItems.length + " kalem"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                        }
                    }

                    // Hızlı Ekleme Çubuğu
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        TextField {
                            id: txtExpName
                            Layout.fillWidth: true
                            placeholderText: "Kira / Mutfak / Fatura"
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm

                            background: Rectangle {
                                color: Theme.bgInput
                                radius: Theme.radiusSm
                                border.color: Theme.borderSubtle
                                border.width: 1
                            }
                        }

                        TextField {
                            id: txtExpAmount
                            Layout.preferredWidth: 90
                            placeholderText: "Tutar"
                            color: Theme.textPrimary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            inputMethodHints: Qt.ImhFormattedNumbersOnly

                            background: Rectangle {
                                color: Theme.bgInput
                                radius: Theme.radiusSm
                                border.color: Theme.borderSubtle
                                border.width: 1
                            }
                        }

                        Rectangle {
                            width: 32
                            height: 32
                            radius: Theme.radiusSm
                            color: Theme.bearRed

                            ModernIcon {
                                anchors.centerIn: parent
                                name: "plus"
                                color: Theme.textInverse
                                size: 14
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var amt = parseFloat(txtExpAmount.text.replace(",", "."))
                                    if (txtExpName.text.trim() && !isNaN(amt) && amt > 0) {
                                        planningController.addBudgetItem("EXPENSE", txtExpName.text.trim(), amt)
                                        txtExpName.text = ""
                                        txtExpAmount.text = ""
                                    }
                                }
                            }
                        }
                    }

                    // Liste
                    ListView {
                        id: expListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: planningController.expenseItems

                        ScrollBar.vertical: ModernScrollBar {}

                        delegate: Rectangle {
                            width: expListView.width
                            height: 38
                            radius: Theme.radiusSm
                            color: Theme.bgSecondary

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceSm
                                anchors.rightMargin: Theme.spaceSm
                                spacing: Theme.spaceSm

                                Text {
                                    text: modelData.name
                                    color: Theme.textPrimary
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: modelData.amountFormatted
                                    color: Theme.bearRed
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                }

                                // Pin Butonu (Sabitleme)
                                Rectangle {
                                    width: 24
                                    height: 24
                                    radius: Theme.radiusXs
                                    color: modelData.isPinned ? Theme.accentSoft : (btnPinExpMouse.containsMouse ? Theme.bgCardHover : "transparent")
                                    border.color: modelData.isPinned ? Theme.accent : "transparent"
                                    border.width: 1

                                    ModernIcon {
                                        anchors.centerIn: parent
                                        name: "bookmark"
                                        color: modelData.isPinned ? Theme.accent : (btnPinExpMouse.containsMouse ? Theme.textPrimary : Theme.textMuted)
                                        size: 13
                                    }

                                    ToolTip.visible: btnPinExpMouse.containsMouse
                                    ToolTip.text: modelData.isPinned ? "Sabitlendi (Her ay otomatik gelir) - Kaldırmak için tıkla" : "Bu kalemi sabitle (Gelecek aylara aktar)"
                                    ToolTip.delay: 300

                                    MouseArea {
                                        id: btnPinExpMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: planningController.togglePinItem("EXPENSE", modelData.name, modelData.amount, !modelData.isPinned)
                                    }
                                }

                                Rectangle {
                                    width: 24
                                    height: 24
                                    radius: Theme.radiusXs
                                    color: btnDelExpMouse.containsMouse ? Theme.bearRedSoft : "transparent"

                                    ModernIcon {
                                        anchors.centerIn: parent
                                        name: "trash"
                                        color: btnDelExpMouse.containsMouse ? Theme.bearRed : Theme.textMuted
                                        size: 12
                                    }

                                    MouseArea {
                                        id: btnDelExpMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: planningController.removeBudgetItem("EXPENSE", index)
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
