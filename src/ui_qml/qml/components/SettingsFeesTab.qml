import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Ücretler: BIST komisyonu, varlık komisyonu ve BSMV (yüzdesel oran veya sabit tutar, varsayılan 0).
ColumnLayout {
    id: root

    readonly property bool hasController: typeof feeSettingsController !== "undefined"

    // Ayarlar ekranındaki global toast'a iletilir
    signal notify(bool success, string message)

    Layout.fillWidth: true
    spacing: 16

    Connections {
        target: root.hasController ? feeSettingsController : null
        function onNotify(success, message) { root.notify(success, message) }
    }

    // Etiket + tür seçici (Oran % / Sabit) + değer girişi satırı
    component RateRow: RowLayout {
        id: rateRow
        property string label: ""
        property string hint: ""
        property string mode: "PCT"
        property alias text: field.text
        signal modeSelected(string newMode)

        Layout.fillWidth: true
        spacing: Theme.spaceSm

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Text {
                text: rateRow.label
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
            }
            Text {
                Layout.fillWidth: true
                text: rateRow.hint
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                wrapMode: Text.WordWrap
            }
        }

        // Oran (%) / Sabit seçici
        Rectangle {
            Layout.preferredHeight: 36
            Layout.preferredWidth: modeRow.implicitWidth + 6
            radius: Theme.radiusSm
            color: Theme.bgInput
            border.color: Theme.borderSubtle
            border.width: 1

            Row {
                id: modeRow
                anchors.centerIn: parent
                spacing: 3

                Repeater {
                    model: [
                        { key: "PCT", label: Strings.settingsFeesModePct },
                        { key: "FIXED", label: Strings.settingsFeesModeFixed }
                    ]

                    Rectangle {
                        height: 28
                        width: modeText.implicitWidth + 16
                        radius: Theme.radiusXs
                        color: rateRow.mode === modelData.key
                               ? Theme.primary
                               : (modeMouse.containsMouse ? Theme.bgCardHover : "transparent")

                        Text {
                            id: modeText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: rateRow.mode === modelData.key ? "#FFFFFF" : Theme.textSecondary
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            font.weight: rateRow.mode === modelData.key ? Font.DemiBold : Font.Normal
                        }

                        MouseArea {
                            id: modeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: rateRow.modeSelected(modelData.key)
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 110
            Layout.preferredHeight: 38
            radius: Theme.radiusSm
            color: Theme.bgInput
            border.color: field.activeFocus ? Theme.primary : Theme.borderSubtle
            border.width: 1

            TextInput {
                id: field
                anchors.fill: parent
                anchors.margins: 8
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                clip: true
                validator: RegularExpressionValidator {
                    regularExpression: rateRow.mode === "FIXED"
                                       ? /^[0-9]{0,6}([.,][0-9]{0,4})?$/
                                       : /^[0-9]{0,3}([.,][0-9]{0,4})?$/
                }
            }
        }

        Text {
            Layout.preferredWidth: 58
            text: rateRow.mode === "FIXED" ? Strings.settingsFeesFixedUnit : "%"
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
        }
    }

    Text {
        text: Strings.settingsFeesTitle
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontXs
        font.weight: Font.Bold
        font.letterSpacing: 0.5
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: feesColumn.implicitHeight + 32
        radius: Theme.radiusMd
        color: Theme.bgSecondary
        border.color: Theme.borderSubtle
        border.width: 1

        ColumnLayout {
            id: feesColumn
            anchors.fill: parent
            anchors.margins: 16
            spacing: 14

            Text {
                Layout.fillWidth: true
                text: Strings.settingsFeesDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                wrapMode: Text.WordWrap
            }

            RateRow {
                id: bistRow
                label: Strings.settingsFeesBist
                hint: Strings.settingsFeesBistHint
                text: root.hasController ? feeSettingsController.bistCommission : "0"
                mode: root.hasController ? feeSettingsController.bistMode : "PCT"
                onModeSelected: function(newMode) {
                    if (root.hasController) feeSettingsController.setMode("bist", newMode)
                }
            }

            RateRow {
                id: assetRow
                label: Strings.settingsFeesAsset
                hint: Strings.settingsFeesAssetHint
                text: root.hasController ? feeSettingsController.assetCommission : "0"
                mode: root.hasController ? feeSettingsController.assetMode : "PCT"
                onModeSelected: function(newMode) {
                    if (root.hasController) feeSettingsController.setMode("asset", newMode)
                }
            }

            RateRow {
                id: bsmvRow
                label: Strings.settingsFeesBsmv
                hint: Strings.settingsFeesBsmvHint
                text: root.hasController ? feeSettingsController.bsmv : "0"
                mode: root.hasController ? feeSettingsController.bsmvMode : "PCT"
                onModeSelected: function(newMode) {
                    if (root.hasController) feeSettingsController.setMode("bsmv", newMode)
                }
            }

            ModernButton {
                text: Strings.btnSave
                enabled: root.hasController
                onClicked: feeSettingsController.save(bistRow.text, assetRow.text, bsmvRow.text)
            }
        }
    }
}
