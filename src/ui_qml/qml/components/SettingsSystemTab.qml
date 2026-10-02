import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Sistem: otomatik canlı fiyat yenileme ayarı ve sistemi sıfırlama.
ColumnLayout {
    id: root

    readonly property bool hasController: typeof systemController !== "undefined"
    readonly property bool resetBusy: hasController && systemController.isResetting

    // Ayarlar ekranındaki global toast'a iletilir
    signal notify(bool success, string message)

    spacing: 16

    Connections {
        target: root.hasController ? systemController : null
        function onNotification(success, message) { root.notify(success, message) }
    }

    // Otomatik fiyat yenileme
    ModernCard {
        Layout.fillWidth: true
        implicitHeight: refreshColumn.implicitHeight + Theme.spaceLg * 2

        ColumnLayout {
            id: refreshColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceSm

            Text {
                text: Strings.sysRefreshTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
            }
            Text {
                text: Strings.sysRefreshDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceMd

                Switch {
                    id: swRefresh
                    text: Strings.sysRefreshEnable
                    checked: root.hasController && systemController.liveRefreshEnabled
                    onToggled: systemController.setLiveRefreshEnabled(checked)
                }

                ModernComboBox {
                    id: cmbInterval
                    implicitWidth: 120
                    enabled: swRefresh.checked
                    model: root.hasController ? systemController.intervalOptions : []
                    textRole: "label"
                    currentIndex: {
                        if (!root.hasController) return 0
                        const opts = systemController.intervalOptions
                        for (let i = 0; i < opts.length; i++) {
                            if (opts[i].minutes === systemController.liveRefreshInterval) return i
                        }
                        return 0
                    }
                    onActivated: systemController.setLiveRefreshInterval(model[currentIndex].minutes)
                }

                ModernButton {
                    text: Strings.sysRefreshNow
                    iconName: "refresh"
                    variant: "secondary"
                    enabled: root.hasController && swRefresh.checked && !systemController.isRefreshing
                    onClicked: systemController.refreshNow()
                }
            }

            Text {
                visible: root.hasController && systemController.lastRefreshText !== ""
                text: Strings.sysRefreshLast + " " + (root.hasController ? systemController.lastRefreshText : "")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
        }
    }

    // Sistem sıfırlama
    ModernCard {
        Layout.fillWidth: true
        implicitHeight: resetColumn.implicitHeight + Theme.spaceLg * 2

        ColumnLayout {
            id: resetColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceSm

            Text {
                text: Strings.sysResetTitle
                color: Theme.bearRed
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
            }
            Text {
                text: Strings.sysResetDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            ModernButton {
                text: Strings.sysResetButton
                iconName: "trash-2"
                variant: "danger"
                enabled: root.hasController && systemController.resetAvailable && !root.resetBusy
                onClicked: confirmReset.ask(Strings.sysResetConfirmTitle, Strings.sysResetConfirmMessage, Strings.sysResetButton)
            }
        }
    }

    ConfirmDialog {
        id: confirmReset
        parent: Overlay.overlay
        onConfirmed: systemController.resetAll()
    }
}
