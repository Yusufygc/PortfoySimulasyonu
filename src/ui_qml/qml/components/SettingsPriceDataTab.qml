import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Fiyat Verisi: eksik gün analizi, güncelleme, silme ve rapor kopyalama.
ColumnLayout {
    id: root

    readonly property bool hasController: typeof priceDataController !== "undefined"
    readonly property bool serviceOk: hasController && priceDataController.serviceAvailable
    readonly property bool busy: hasController && priceDataController.isBusy
    readonly property string scopeValue: {
        if (!hasController || cmbScope.currentIndex < 0) return "all_active"
        const opts = priceDataController.scopeOptions
        return cmbScope.currentIndex < opts.length ? opts[cmbScope.currentIndex].value : "all_active"
    }

    // Ayarlar ekranındaki global toast'a iletilir
    signal notify(bool success, string message)

    spacing: 16

    Connections {
        target: root.hasController ? priceDataController : null
        function onNotification(success, message) { root.notify(success, message) }
        function onRangeChanged() {
            txtStart.text = priceDataController.startText
            txtEnd.text = priceDataController.endText
        }
    }

    // Başlık
    RowLayout {
        Layout.fillWidth: true
        Text {
            text: Strings.pdTitle
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            font.weight: Font.Bold
            Layout.fillWidth: true
        }
        CheckBox {
            id: chkProblem
            text: Strings.pdProblemOnly
            checked: root.hasController && priceDataController.problemOnly
            onToggled: priceDataController.setProblemOnly(checked)
            contentItem: Text {
                text: chkProblem.text
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                leftPadding: chkProblem.indicator.width + 6
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    Text {
        text: root.serviceOk ? Strings.pdDesc : Strings.pdServiceMissing
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    // Özet kartları
    Flow {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        Repeater {
            model: [
                { label: Strings.pdStocks, value: root.hasController ? priceDataController.stockCount : "-" },
                { label: Strings.pdMissing, value: root.hasController ? priceDataController.missingCount : "-" },
                { label: Strings.pdHolidays, value: root.hasController ? priceDataController.holidayCount : "-" },
                { label: Strings.pdHolidayCandidates, value: root.hasController ? priceDataController.holidayCandidateCount : "-" },
                { label: Strings.pdLatest, value: root.hasController ? priceDataController.latestDate : "-" }
            ]
            Rectangle {
                width: 150
                height: 56
                radius: Theme.radiusSm
                color: Theme.bgSecondary
                border.color: Theme.borderSubtle

                Column {
                    anchors.centerIn: parent
                    spacing: 2
                    Text { text: modelData.label; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontXs; font.weight: Font.Bold; anchors.horizontalCenter: parent.horizontalCenter }
                    Text { text: modelData.value; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontMd; font.weight: Font.Bold; anchors.horizontalCenter: parent.horizontalCenter }
                }
            }
        }
    }

    // Filtre satırı
    Flow {
        Layout.fillWidth: true
        spacing: Theme.spaceMd

        ColumnLayout {
            spacing: Theme.spaceXs
            Text { text: Strings.pdScope; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
            ComboBox {
                id: cmbScope
                implicitWidth: 240
                implicitHeight: 34
                model: root.hasController ? priceDataController.scopeOptions : []
                textRole: "label"
                onActivated: priceDataController.resetRange(root.scopeValue)

                background: Rectangle {
                    color: Theme.bgInput
                    radius: Theme.radiusSm
                    border.color: Theme.borderSubtle
                    border.width: 1
                }

                contentItem: Text {
                    leftPadding: Theme.spaceSm
                    text: cmbScope.displayText
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                delegate: ItemDelegate {
                    width: cmbScope.width
                    highlighted: cmbScope.highlightedIndex === index
                    contentItem: Text {
                        text: modelData.label
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.highlighted ? Theme.bgCardHover : Theme.bgSecondary
                    }
                }

                popup.background: Rectangle {
                    color: Theme.bgSecondary
                    radius: Theme.radiusSm
                    border.color: Theme.borderSubtle
                }
            }
        }

        ColumnLayout {
            spacing: Theme.spaceXs
            Text { text: Strings.pdStart; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
            ModernInput {
                id: txtStart
                implicitWidth: 160
                text: root.hasController ? priceDataController.startText : ""
            }
        }

        ColumnLayout {
            spacing: Theme.spaceXs
            Text { text: Strings.pdEnd; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
            ModernInput {
                id: txtEnd
                implicitWidth: 160
                text: root.hasController ? priceDataController.endText : ""
            }
        }
    }

    // Aksiyon butonları
    Flow {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        ModernButton {
            text: Strings.pdBtnAnalyze
            variant: "primary"
            enabled: root.serviceOk && !root.busy
            onClicked: priceDataController.analyze(txtStart.text, txtEnd.text, root.scopeValue)
        }
        ModernButton {
            text: Strings.pdBtnUpdateMissing
            variant: "secondary"
            enabled: root.serviceOk && !root.busy
            onClicked: priceDataController.updateMissing(txtStart.text, txtEnd.text, root.scopeValue)
        }
        ModernButton {
            text: Strings.pdBtnUpdateSelected
            variant: "secondary"
            enabled: root.serviceOk && !root.busy && priceDataController.selectedStockId > 0
            onClicked: priceDataController.updateSelected(priceDataController.selectedStockId, txtStart.text, txtEnd.text, root.scopeValue)
        }
        ModernButton {
            text: Strings.pdBtnUpdateLatest
            variant: "secondary"
            enabled: root.serviceOk && !root.busy
            onClicked: priceDataController.updateFromLatest(root.scopeValue)
        }
        ModernButton {
            text: Strings.pdBtnDelete
            variant: "danger"
            enabled: root.serviceOk && !root.busy
            onClicked: deleteConfirm.visible = true
        }
        ModernButton {
            text: Strings.pdBtnCopy
            variant: "ghost"
            enabled: root.hasController && priceDataController.hasReport
            onClicked: priceDataController.copyReport()
        }
    }

    // Silme onayı (satır içi)
    Rectangle {
        id: deleteConfirm
        visible: false
        Layout.fillWidth: true
        implicitHeight: confirmRow.implicitHeight + Theme.spaceMd
        radius: Theme.radiusSm
        color: Theme.dangerSoft
        border.color: Theme.danger

        RowLayout {
            id: confirmRow
            anchors.fill: parent
            anchors.margins: Theme.spaceSm
            spacing: Theme.spaceSm

            Text {
                text: Strings.pdDeleteConfirm
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            ModernButton {
                text: Strings.btnCancel
                variant: "secondary"
                onClicked: deleteConfirm.visible = false
            }
            ModernButton {
                text: Strings.btnConfirmDelete
                variant: "danger"
                onClicked: {
                    deleteConfirm.visible = false
                    priceDataController.deleteRange(txtStart.text, txtEnd.text, root.scopeValue)
                }
            }
        }
    }

    // Meşgul göstergesi
    RowLayout {
        visible: root.busy
        Layout.fillWidth: true
        spacing: Theme.spaceSm
        BusyIndicator { running: root.busy; implicitWidth: 22; implicitHeight: 22 }
        Text {
            text: root.hasController ? priceDataController.busyText : ""
            color: Theme.accent
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
        }
    }

    // İçerik: tablo + detay
    RowLayout {
        Layout.fillWidth: true
        Layout.preferredHeight: 320
        spacing: Theme.spaceMd

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 3
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            clip: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    color: Theme.bgCard

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceSm

                        Repeater {
                            model: [
                                { t: Strings.pdThTicker, w: 80 }, { t: Strings.pdThLastDate, w: 90 },
                                { t: Strings.pdThMissing, w: 60 }, { t: Strings.pdThStatus, w: -1 },
                                { t: Strings.pdThFirstMissing, w: 90 }, { t: Strings.pdThLastMissing, w: 90 }
                            ]
                            Text {
                                text: modelData.t
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                Layout.preferredWidth: modelData.w > 0 ? modelData.w : 0
                                Layout.fillWidth: modelData.w < 0
                            }
                        }
                    }
                }

                ListView {
                    id: healthList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.hasController ? priceDataController.rows : []
                    ScrollBar.vertical: ModernScrollBar {}

                    delegate: Rectangle {
                        width: healthList.width
                        height: 32
                        color: modelData.stockId === priceDataController.selectedStockId
                               ? Theme.accentSoft
                               : (rowMouse.containsMouse ? Theme.bgCardHover : "transparent")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spaceSm
                            anchors.rightMargin: Theme.spaceSm
                            spacing: Theme.spaceSm

                            Text { text: modelData.ticker; color: Theme.accent; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                            Text { text: modelData.lastDate; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                            Text { text: modelData.missingCount; color: modelData.missingCount > 0 ? Theme.bearRed : Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 60 }
                            Text { text: modelData.status; color: modelData.healthy ? Theme.bullGreen : Theme.bearRed; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { text: modelData.firstMissing; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                            Text { text: modelData.lastMissing; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                        }

                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: priceDataController.selectStock(modelData.stockId)
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: healthList.count === 0
                        text: Strings.pdWaiting
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 2
            radius: Theme.radiusSm
            color: Theme.bgSecondary
            border.color: Theme.borderSubtle
            clip: true

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceSm
                clip: true
                ScrollBar.vertical: ModernScrollBar {}

                Text {
                    width: parent.width
                    text: root.hasController && priceDataController.detailHtml !== "" ? priceDataController.detailHtml : Strings.pdWaiting
                    textFormat: Text.RichText
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
