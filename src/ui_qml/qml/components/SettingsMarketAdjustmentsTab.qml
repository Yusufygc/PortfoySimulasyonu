import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Piyasa Düzeltmeleri: tüm BIST için veri güdümlü sermaye artırımı/bölünme adayları; onay, red, geri alma.
ColumnLayout {
    id: root

    property string selectedKey: ""
    readonly property bool hasController: typeof marketAdjustmentController !== "undefined"
    readonly property bool servicesOk: hasController && marketAdjustmentController.serviceAvailable
    readonly property bool busy: hasController && marketAdjustmentController.isBusy
    readonly property var statusKeys: ["CANDIDATE", "", "CONFIRMED", "IGNORED", "NO_BREAK"]
    readonly property var selected: {
        if (!hasController) return null
        const list = marketAdjustmentController.actions
        for (let i = 0; i < list.length; i++) {
            if (list[i].ticker + "|" + list[i].dateIso === root.selectedKey) return list[i]
        }
        return null
    }

    // Ayarlar ekranındaki global toast'a iletilir
    signal notify(bool success, string message)

    spacing: 16

    function reload() {
        if (!hasController) return
        const year = parseInt(txtSince.text)
        marketAdjustmentController.refresh(statusKeys[cmbStatus.currentIndex], txtTicker.text, isNaN(year) ? 0 : year)
    }

    Component.onCompleted: reload()

    Connections {
        target: root.hasController ? marketAdjustmentController : null
        function onNotification(success, message) { root.notify(success, message) }
        function onAdjustmentsChanged() { root.reload() }
    }

    onSelectedChanged: {
        if (selected) txtFactor.text = selected.factorText
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        Text {
            text: Strings.maTitle
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            font.weight: Font.Bold
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        ModernButton {
            text: Strings.maBtnScan
            iconName: "search"
            variant: "primary"
            enabled: root.servicesOk && !root.busy
            onClicked: marketAdjustmentController.scan()
        }
    }

    Text {
        text: root.servicesOk ? Strings.maDesc : Strings.maServiceMissing
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    Text {
        visible: root.hasController && marketAdjustmentController.totalCount > 0
        text: root.hasController
              ? Strings.maCountShown + marketAdjustmentController.actions.length + " / " + marketAdjustmentController.totalCount
              : ""
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
    }

    // Filtreler
    Flow {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        ModernComboBox {
            id: cmbStatus
            implicitWidth: 170
            model: [Strings.maFilterCandidate, Strings.maFilterAll, Strings.maFilterConfirmed,
                    Strings.maFilterIgnored, Strings.maFilterNoBreak]
            onActivated: root.reload()
        }
        ModernInput {
            id: txtTicker
            implicitWidth: 130
            placeholderText: Strings.maTicker
            onAccepted: root.reload()
        }
        ModernInput {
            id: txtSince
            implicitWidth: 130
            text: "2018"
            placeholderText: Strings.maSince
            onAccepted: root.reload()
        }
        ModernButton {
            text: Strings.caBtnRefreshList
            iconName: "refresh"
            variant: "secondary"
            onClicked: root.reload()
        }
    }

    // Tablo
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 320
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
                            { t: Strings.maTicker, w: 80 }, { t: Strings.maThDate, w: 90 },
                            { t: Strings.maThFactor, w: 80 }, { t: Strings.maThObserved, w: 100 },
                            { t: Strings.maThConfidence, w: 60 }, { t: Strings.maThStatus, w: 150 },
                            { t: Strings.maThSource, w: -1 }
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
                id: actionList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.hasController ? marketAdjustmentController.actions : []
                ScrollBar.vertical: ModernScrollBar {}

                delegate: Rectangle {
                    readonly property string rowKey: modelData.ticker + "|" + modelData.dateIso
                    width: actionList.width
                    height: 34
                    color: rowKey === root.selectedKey
                           ? Theme.accentSoft
                           : (rowMouse.containsMouse ? Theme.bgCardHover : "transparent")

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceSm

                        Text { text: modelData.ticker; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                        Text { text: modelData.dateText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                        Text { text: modelData.factorText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 80 }
                        Text { text: modelData.observedText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 100 }
                        Text { text: modelData.confidenceText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 60 }
                        Text {
                            text: modelData.statusLabel
                            color: modelData.isActive ? Theme.bullGreen : Theme.warning
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.preferredWidth: 150
                            elide: Text.ElideRight
                        }
                        Text { text: modelData.source; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.fillWidth: true }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.selectedKey = rowKey
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: actionList.count === 0
                    text: Strings.maEmpty
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }
    }

    // Seçili olay: faktör düzenleme ve karar
    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceXs

        Text {
            text: root.selected === null ? Strings.maNoSelection : (root.selected.note !== "" ? root.selected.note : Strings.maNoSelection)
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Text {
            text: Strings.maFactorLabel
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
        }
    }

    Flow {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        ModernInput {
            id: txtFactor
            implicitWidth: 130
            enabled: root.selected !== null
        }
        ModernButton {
            text: Strings.maBtnConfirm
            variant: "primary"
            enabled: root.selected !== null && root.selected.canConfirm && !root.busy
            onClicked: marketAdjustmentController.confirm(root.selected.ticker, root.selected.dateIso, txtFactor.text)
        }
        ModernButton {
            text: Strings.maBtnIgnore
            variant: "danger"
            enabled: root.selected !== null && root.selected.status === "CANDIDATE" && !root.busy
            onClicked: marketAdjustmentController.ignore(root.selected.ticker, root.selected.dateIso)
        }
        ModernButton {
            text: Strings.maBtnReopen
            variant: "secondary"
            enabled: root.selected !== null && (root.selected.isActive || root.selected.status === "IGNORED") && !root.busy
            onClicked: marketAdjustmentController.reopen(root.selected.ticker, root.selected.dateIso)
        }
    }
}
