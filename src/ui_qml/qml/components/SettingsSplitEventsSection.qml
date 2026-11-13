import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Kurumsal Aksiyonlar üst bölümü: otomatik/uygulanmış hisse bölünmeleri, otomatik uygulama anahtarı, geri alma.
ColumnLayout {
    id: root

    readonly property bool hasController: typeof splitEventsController !== "undefined"
    readonly property bool ok: hasController && splitEventsController.available
    readonly property bool busy: hasController && splitEventsController.isBusy

    signal notify(bool success, string message)

    spacing: Theme.spaceSm

    Component.onCompleted: { if (ok) splitEventsController.refresh() }

    Connections {
        target: root.hasController ? splitEventsController : null
        function onNotification(success, message) { root.notify(success, message) }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceSm

        Text {
            text: Strings.splitTitle
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            font.weight: Font.Bold
            Layout.fillWidth: true
        }
        Switch {
            enabled: root.ok
            checked: root.ok && splitEventsController.autoApply
            onToggled: splitEventsController.setAutoApply(checked)
        }
        Text {
            text: Strings.splitAutoApply
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
        }
        ModernButton {
            text: Strings.splitBtnScan
            iconName: "search"
            variant: "secondary"
            enabled: root.ok && !root.busy
            onClicked: splitEventsController.scanNow()
        }
    }

    Text {
        text: root.ok ? Strings.splitDesc : Strings.splitUnavailable
        color: Theme.textSecondary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSm
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 180
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
                            { t: Strings.caThTicker, w: 70 }, { t: Strings.caThRatio, w: 70 },
                            { t: Strings.caThExDate, w: 85 }, { t: Strings.splitThSources, w: 150 },
                            { t: Strings.splitThLedgers, w: 160 }, { t: Strings.splitThPrices, w: 150 },
                            { t: Strings.splitThStatus, w: -1 }
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
                id: eventList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.ok ? splitEventsController.events : []
                ScrollBar.vertical: ModernScrollBar {}

                delegate: Rectangle {
                    width: eventList.width
                    height: 36
                    color: "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceSm

                        Text { text: modelData.ticker; color: Theme.textPrimary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.Bold; Layout.preferredWidth: 70 }
                        Text { text: modelData.ratioText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 70 }
                        Text { text: modelData.exDateText; color: Theme.textSecondary; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; Layout.preferredWidth: 85 }
                        Text { text: modelData.sourcesText; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.preferredWidth: 150 }
                        Text {
                            text: modelData.ledgersText + (modelData.cashText !== "" ? " · " + modelData.cashText : "")
                            color: Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            elide: Text.ElideRight
                            Layout.preferredWidth: 160
                        }
                        Text { text: modelData.pricesText; color: Theme.textMuted; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm; elide: Text.ElideRight; Layout.preferredWidth: 150 }
                        Text {
                            text: modelData.statusText + " · " + (modelData.auto ? Strings.splitAuto : Strings.splitManual)
                            color: modelData.applied ? Theme.textPositive : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            Layout.fillWidth: true
                        }
                        ModernButton {
                            text: Strings.splitBtnRevert
                            variant: "danger"
                            visible: modelData.applied
                            enabled: !root.busy
                            onClicked: splitEventsController.revert(modelData.id)
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: eventList.count === 0
                    text: Strings.splitEmpty
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                }
            }
        }
    }
}
