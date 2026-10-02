import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Dialogs
import "../theme"

// Excel raporu dışa aktarım diyaloğu: tarih aralığı + kayıt konumu seçimi.
Rectangle {
    id: root

    property bool isOpen: false
    property string title: Strings.excelDialogTitle
    property string defaultFileName: "Portfoy_Raporu.xlsx"
    property string firstDateText: ""
    property bool useRange: false
    property string statusText: ""

    // Başlangıç/bitiş boş = ilk işlemden bugüne. Dosya yolu boşsa servis varsayılanını kullanır.
    signal exportRequested(string startText, string endText, string filePath)

    anchors.fill: parent
    color: "#99000000"
    visible: opacity > 0
    opacity: isOpen ? 1.0 : 0.0
    z: 1000

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function todayText() {
        const d = new Date()
        return String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") + "." + d.getFullYear()
    }

    function open(firstDate, fileName) {
        firstDateText = firstDate || ""
        defaultFileName = fileName || "Portfoy_Raporu.xlsx"
        useRange = false
        txtStart.text = firstDateText
        txtEnd.text = todayText()
        txtFile.text = ""
        statusText = ""
        isOpen = true
    }

    function close() {
        isOpen = false
    }

    FileDialog {
        id: fileDialog
        title: Strings.excelDialogChooseFile
        fileMode: FileDialog.SaveFile
        nameFilters: ["Excel (*.xlsx)"]
        defaultSuffix: "xlsx"
        currentFile: "file:///" + root.defaultFileName
        onAccepted: txtFile.text = String(selectedFile).replace(/^file:\/\/\//, "")
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    ModernCard {
        anchors.centerIn: parent
        width: Math.min(480, root.width - 32)
        implicitHeight: dialogColumn.implicitHeight + Theme.spaceLg * 2
        height: Math.min(root.height - 32, implicitHeight)

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            id: dialogColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceMd

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: root.title
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMd
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                Item {
                    width: 24
                    height: 24
                    ModernIcon { name: "close"; size: 16; color: Theme.textMuted; anchors.centerIn: parent }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                ModernButton {
                    text: Strings.excelModeAll
                    variant: root.useRange ? "secondary" : "primary"
                    onClicked: root.useRange = false
                }
                ModernButton {
                    text: Strings.excelModeRange
                    variant: root.useRange ? "primary" : "secondary"
                    onClicked: root.useRange = true
                }
            }

            RowLayout {
                visible: root.useRange
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    spacing: Theme.spaceXs
                    Text { text: Strings.excelLabelStart; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                    ModernInput { id: txtStart; Layout.fillWidth: true; placeholder: "GG.AA.YYYY" }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    spacing: Theme.spaceXs
                    Text { text: Strings.excelLabelEnd; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                    ModernInput { id: txtEnd; Layout.fillWidth: true; placeholder: "GG.AA.YYYY" }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                Text { text: Strings.excelLabelFile; color: Theme.textSecondary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSm }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm
                    ModernInput {
                        id: txtFile
                        Layout.fillWidth: true
                        placeholder: Strings.excelFilePlaceholder
                    }
                    ModernButton {
                        text: Strings.excelBtnBrowse
                        variant: "secondary"
                        onClicked: fileDialog.open()
                    }
                }
            }

            Text {
                visible: root.statusText !== ""
                text: root.statusText
                color: Theme.bearRed
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                ModernButton {
                    Layout.fillWidth: true
                    text: Strings.btnCancel
                    variant: "secondary"
                    onClicked: root.close()
                }
                ModernButton {
                    Layout.fillWidth: true
                    text: Strings.excelBtnExport
                    variant: "primary"
                    onClicked: {
                        const start = root.useRange ? txtStart.text.trim() : ""
                        const end = root.useRange ? txtEnd.text.trim() : ""
                        root.close()
                        root.exportRequested(start, end, txtFile.text.trim())
                    }
                }
            }
        }
    }
}
