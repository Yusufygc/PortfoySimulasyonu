import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property bool isOpen: false
    signal closed()

    anchors.fill: parent
    color: "#80000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0

    Behavior on opacity { NumberAnimation { duration: 180 } }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        id: dialogCard
        anchors.centerIn: parent
        width: 380
        implicitHeight: 400
        scale: root.isOpen ? 1.0 : 0.95

        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        MouseArea {
            anchors.fill: parent
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Sermaye ve Nakit Yönetimi"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
                Text {
                    text: "✕"
                    font.pixelSize: 16
                    color: Theme.textMuted
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            // Yatır / Çek Butonları
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 36
                    radius: Theme.radiusSm
                    color: isDeposit ? Theme.accent : Theme.bgInput
                    border.color: isDeposit ? Theme.accent : Theme.borderSubtle
                    border.width: 1

                    property bool isDeposit: actionToggle.state === "deposit"

                    Text {
                        anchors.centerIn: parent
                        text: "💰 Nakit Yatır"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: parent.isDeposit ? "#ffffff" : Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: actionToggle.state = "deposit"
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 36
                    radius: Theme.radiusSm
                    color: !isDeposit ? Theme.accent : Theme.bgInput
                    border.color: !isDeposit ? Theme.accent : Theme.borderSubtle
                    border.width: 1

                    property bool isDeposit: actionToggle.state === "deposit"

                    Text {
                        anchors.centerIn: parent
                        text: "🏦 Nakit Çek"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.Bold
                        color: !parent.isDeposit ? "#ffffff" : Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: actionToggle.state = "withdraw"
                    }
                }
            }

            Item { id: actionToggle; state: "deposit" }

            // Mevcut Bakiye Göstergesi
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 46
                radius: Theme.radiusSm
                color: Theme.bgInput

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    Text { text: "Mevcut Bakiye:"; font.pixelSize: 12; color: Theme.textSecondary; Layout.fillWidth: true }
                    Text { text: dashboardController.cashBalance; font.pixelSize: 13; font.weight: Font.Bold; color: Theme.textPrimary }
                }
            }

            // Tutar Girişi
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "Tutar (₺)"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: amountInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    TextInput {
                        id: amountInput
                        anchors.fill: parent
                        anchors.margins: 10
                        text: "10000"
                        font.family: Theme.monoFontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        validator: DoubleValidator { bottom: 1.0; top: 100000000.0; decimals: 2 }
                    }
                }
            }

            // Not / Açıklama
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "Açıklama / Not"; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: noteInput.activeFocus ? Theme.borderFocus : Theme.borderSubtle
                    border.width: 1

                    TextInput {
                        id: noteInput
                        anchors.fill: parent
                        anchors.margins: 10
                        text: "Maaş tasarrufu birikimi"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        color: Theme.textPrimary
                    }
                }
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                ModernButton {
                    Layout.fillWidth: true
                    text: "İptal"
                    variant: "secondary"
                    onClicked: root.close()
                }

                ModernButton {
                    Layout.fillWidth: true
                    text: actionToggle.state === "deposit" ? "Sermaye Yatır" : "Nakit Çek"
                    variant: "primary"
                    onClicked: {
                        const amount = parseFloat(amountInput.text) || 0.0
                        dashboardController.manageCapital(actionToggle.state, amount, noteInput.text)
                        root.close()
                    }
                }
            }
        }
    }

    function open() {
        root.isOpen = true
    }

    function close() {
        root.isOpen = false
        root.closed()
    }
}
