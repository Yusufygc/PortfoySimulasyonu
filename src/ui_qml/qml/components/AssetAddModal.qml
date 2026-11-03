import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Varlık ekleme: hazır katalogdan (altın, gümüş, platin, kripto) tek tıkla ya da sembolle (ABD hissesi, kripto, emtia).
// Sembol arka planda fiyat kaynağında doğrulanır; sonuç assetsController.assetAdded sinyaliyle gelir.
Rectangle {
    id: root

    property bool isOpen: false
    readonly property bool busy: assetsController.busy

    readonly property var classOptions: [
        { key: "US_STOCK", label: Strings.allocClassUs },
        { key: "CRYPTO", label: Strings.allocClassCrypto },
        { key: "PRECIOUS_METAL", label: Strings.allocClassMetal }
    ]

    signal closed()

    anchors.fill: parent
    color: "#80000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function open() {
        symbolInput.text = ""
        nameInput.text = ""
        classCombo.currentIndex = 0
        root.isOpen = true
    }

    function close() {
        root.isOpen = false
        root.closed()
    }

    function isAdded(symbol) {
        const list = assetsController.assets
        for (let i = 0; i < list.length; i++) {
            if (list[i].symbol === symbol) return true
        }
        return false
    }

    Connections {
        target: assetsController
        function onAssetAdded(success, message) {
            if (success && root.isOpen) root.close()
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: if (!root.busy) root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(480, parent.width - Theme.spaceLg * 2)
        implicitHeight: Math.min(parent.height - Theme.spaceLg * 2, contentColumn.implicitHeight + Theme.spaceLg * 2)
        scale: root.isOpen ? 1.0 : 0.95

        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        MouseArea { anchors.fill: parent }

        ScrollView {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: contentColumn
                width: parent.width
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: Strings.assetAddTitle
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontLg
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                        Layout.fillWidth: true
                    }
                    Item {
                        width: 24
                        height: 24
                        ModernIcon { name: "close"; size: 16; color: Theme.textMuted; anchors.centerIn: parent }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            enabled: !root.busy
                            onClicked: root.close()
                        }
                    }
                }

                // Hazır varlıklar
                Text {
                    text: Strings.assetAddCatalog
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs

                    Repeater {
                        model: assetsController.catalog

                        ModernButton {
                            required property var modelData
                            readonly property bool added: root.isAdded(modelData.key)
                            text: modelData.name + (added ? "  ✓ " + Strings.assetAddedBadge : "")
                            variant: added ? "ghost" : "secondary"
                            enabled: !added && !root.busy
                            implicitHeight: 30
                            onClicked: assetsController.addCatalogAsset(modelData.key)
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.borderSubtle }

                // Sembolle ekle
                Text {
                    text: Strings.assetAddCustom
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    color: Theme.textMuted
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.assetLabelSymbol; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernInput {
                            id: symbolInput
                            Layout.fillWidth: true
                            implicitHeight: 36
                            font.family: Theme.monoFontFamily
                            font.weight: Font.Bold
                            enabled: !root.busy
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.assetLabelName; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernInput {
                            id: nameInput
                            Layout.fillWidth: true
                            implicitHeight: 36
                            enabled: !root.busy
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: 4
                        Text { text: Strings.assetLabelClass; font.pixelSize: 11; font.weight: Font.Bold; color: Theme.textMuted }
                        ModernComboBox {
                            id: classCombo
                            Layout.fillWidth: true
                            model: root.classOptions
                            textRole: "label"
                            enabled: !root.busy
                        }
                    }

                }

                Text {
                    text: Strings.assetAddHint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    ModernButton {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        text: Strings.btnCancel
                        variant: "secondary"
                        enabled: !root.busy
                        onClicked: root.close()
                    }

                    ModernButton {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        text: root.busy ? Strings.assetAdding : Strings.btnAddShort
                        variant: "primary"
                        enabled: !root.busy && symbolInput.text.trim() !== ""
                        onClicked: assetsController.addAsset(
                            symbolInput.text, nameInput.text, root.classOptions[classCombo.currentIndex].key, "")
                    }
                }
            }
        }
    }
}
