import QtQuick
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: root
    property string title: "Sayfa Başlığı"
    property string subtitle: "Bu modül dönüşüm planının sonraki fazında TradingView / QML bileşenleriyle inşa edilecektir."
    property string iconName: "layers"
    property string iconSymbol: ""
    Layout.fillWidth: true
    Layout.fillHeight: true

    ModernCard {
        anchors.centerIn: parent
        implicitWidth: 460
        implicitHeight: 260

        ColumnLayout {
            anchors.centerIn: parent
            spacing: Theme.spaceMd

            ModernIcon {
                name: root.iconName
                size: 40
                color: Theme.accent
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: root.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontLg
                font.weight: Font.Bold
                color: Theme.textPrimary
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: root.subtitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Layout.preferredWidth: 360
                Layout.alignment: Qt.AlignHCenter
            }

            ModernButton {
                text: Strings.btnBackToDashboard || "Dashboard'a Dön"
                iconName: "collapse"
                variant: "secondary"
                Layout.alignment: Qt.AlignHCenter
                onClicked: shellController.navigateTo(0)
            }
        }
    }
}
