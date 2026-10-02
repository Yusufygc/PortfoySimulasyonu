import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Kurumsal Aksiyonlar: KAP/MKK aday listesi, tarama, onaylayıp uygulama, düzenleme, yoksayma.
ColumnLayout {
    id: root

    property int selectedId: -1
    readonly property bool hasController: typeof corporateActionController !== "undefined"
    readonly property bool servicesOk: hasController && corporateActionController.candidateServicesAvailable
    readonly property bool busy: hasController && corporateActionController.isBusy
    readonly property var selected: {
        if (!hasController) return null
        const list = corporateActionController.candidates
        for (let i = 0; i < list.length; i++) {
            if (list[i].id === root.selectedId) return list[i]
        }
        return null
    }

    // Ayarlar ekranındaki global toast'a iletilir
    signal notify(bool success, string message)

    spacing: 16

    Component.onCompleted: {
        if (hasController) corporateActionController.refreshCandidates()
    }

    Connections {
        target: root.hasController ? corporateActionController : null
        function onNotification(success, message) { root.notify(success, message) }
    }

    onSelectedChanged: {
        if (hasController) corporateActionController.selectCandidate(selected ? selected.id : -1)
    }

    // Başlık ve üst butonlar
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        Text {
            text: Strings.caCandTitle
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            font.weight: Font.Bold
            Layout.fillWidth: true
        }

        ModernButton {
            text: Strings.caBtnRefreshList
            iconName: "refresh"
            variant: "secondary"
            enabled: root.servicesOk && !root.busy
            onClicked: corporateActionController.refreshCandidates()
        }

        ModernButton {
            text: Strings.caBtnScan
            iconName: "search"
            variant: "primary"
            enabled: root.servicesOk && !root.busy
            onClicked: corporateActionController.discoverCandidates()
        }
    }

    Text {
        text: root.servicesOk ? Strings.caCandDesc : Strings.caServicesMissing
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    // Tablo
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 300
        radius: Theme.radiusSm
        color: Theme.bgSecondary
        border.color: Theme.borderSubtle
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Başlık satırı
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
                            { t: Strings.caThTicker, w: 80 }, { t: Strings.caThType, w: 80 },
                            { t: Strings.caThStatus, w: 120 }, { t: Strings.caThRatio, w: 80 },
                            { t: Strings.caThSubPrice, w: 90 }, { t: Strings.caThExDate, w: 90 },
                            { t: Strings.caThConfidence, w: 60 }, { t: Strings.caThSource, w: -1 }
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
                id: candidateList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.hasController ? corporateActionController.candidates : []
                ScrollBar.vertical: ModernScrollBar {}

                delegate: Rectangle {
                    width: candidateList.width
                    height: 34
                    color: modelData.id === root.selectedId
                           ? Theme.accentSoft
                           : (rowMouse.containsMouse ? Theme.bgCardHover : "transparent")

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceSm

                        Text { text: modelData.ticker; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.Bold; Layout.preferredWidth: 80 }
                        Text { text: modelData.actionType === "BEDELLI" ? Strings.caTypeBedelli : Strings.caTypeBedelsiz; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 80 }
                        Text {
                            text: Strings.candidateStatusLabel(modelData.status)
                            color: modelData.canApply ? Theme.bullGreen : Theme.warning
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.preferredWidth: 120
                        }
                        Text { text: modelData.ratioText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 80 }
                        Text { text: modelData.subscriptionText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                        Text { text: modelData.exDateText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 90 }
                        Text { text: modelData.confidenceText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 60 }
                        Text { text: modelData.source; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.fillWidth: true }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.selectedId = modelData.id
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: candidateList.count === 0
                    text: Strings.caEmpty
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }
    }

    // Aksiyon butonları
    Flow {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        ModernButton {
            text: Strings.caBtnApprove
            variant: "primary"
            enabled: root.selected !== null && root.selected.canApply && !root.busy
            onClicked: corporateActionController.applyCandidate(root.selected.id)
        }
        ModernButton {
            text: Strings.caBtnEdit
            variant: "secondary"
            enabled: root.selected !== null && !root.busy
            onClicked: editDialog.open(root.selected)
        }
        ModernButton {
            text: Strings.caBtnIgnore
            variant: "danger"
            enabled: root.selected !== null && !root.busy
            onClicked: corporateActionController.ignoreCandidate(root.selected.id)
        }
        ModernButton {
            text: Strings.caBtnSource
            variant: "ghost"
            enabled: root.selected !== null && root.selected.sourceUrl !== ""
            onClicked: corporateActionController.openCandidateSource(root.selected.id)
        }
    }

    // Detay
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 110
        radius: Theme.radiusSm
        color: Theme.bgSecondary
        border.color: Theme.borderSubtle

        ScrollView {
            anchors.fill: parent
            anchors.margins: Theme.spaceSm
            clip: true

            Text {
                width: parent.width
                text: root.selected === null && root.hasController && corporateActionController.detailText === ""
                      ? Strings.caNoSelection
                      : (root.hasController ? corporateActionController.detailText : "")
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
            }
        }
    }

    CorporateActionCandidateEditDialog {
        id: editDialog
        parent: Overlay.overlay
    }
}
