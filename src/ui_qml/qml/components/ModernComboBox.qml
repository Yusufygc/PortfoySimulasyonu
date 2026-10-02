import QtQuick
import QtQuick.Controls
import "../theme"

// Tema uyumlu açılır liste. Model düz metin listesi veya nesne listesi (textRole ile) olabilir.
ComboBox {
    id: root

    implicitHeight: 34
    implicitWidth: 180

    function itemText(item) {
        if (item === undefined || item === null) return ""
        return (typeof item === "object" && root.textRole !== "") ? String(item[root.textRole]) : String(item)
    }

    background: Rectangle {
        color: root.enabled ? Theme.bgInput : Theme.bgSecondary
        radius: Theme.radiusSm
        border.color: root.activeFocus ? Theme.borderFocus : Theme.borderSubtle
        border.width: 1
    }

    contentItem: Text {
        leftPadding: Theme.spaceSm
        rightPadding: 24
        text: root.displayText
        color: root.enabled ? Theme.textPrimary : Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: ModernIcon {
        x: root.width - width - Theme.spaceSm
        y: (root.height - height) / 2
        size: 12
        iconSource: Icons.chevronDown
        color: Theme.textMuted
    }

    delegate: ItemDelegate {
        id: optionItem
        width: root.width
        highlighted: root.highlightedIndex === index
        contentItem: Text {
            text: root.itemText(modelData)
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: optionItem.highlighted ? Theme.bgCardHover : Theme.bgSecondary
        }
    }

    popup: Popup {
        y: root.height + 2
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 2, 260)
        padding: 1

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollBar.vertical: ModernScrollBar {}
        }

        background: Rectangle {
            color: Theme.bgSecondary
            radius: Theme.radiusSm
            border.color: Theme.borderSubtle
        }
    }
}
