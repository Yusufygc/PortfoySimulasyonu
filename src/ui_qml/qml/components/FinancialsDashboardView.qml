import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine
import "../theme"

Item {
    id: root

    property string htmlUrl: ""
    property bool isLoading: false
    property string emptyTitle: Strings.emptyFinancialsTitle
    property string emptySubtitle: Strings.emptyFinancialsSubtitle

    clip: true

    WebEngineView {
        id: webView
        anchors.fill: parent
        backgroundColor: Theme.bgPrimary
        visible: root.htmlUrl !== "" && !root.isLoading

        settings.javascriptEnabled: true
        settings.localContentCanAccessRemoteUrls: true
        settings.localContentCanAccessFileUrls: true

        onJavaScriptConsoleMessage: function(level, message, lineNumber, sourceID) {
            // Silently absorb or log JS messages
        }
    }

    onHtmlUrlChanged: {
        if (root.htmlUrl !== "") {
            webView.url = root.htmlUrl
        }
    }

    // Yükleniyor veya Veri Yok Durumu Göstergesi
    Rectangle {
        anchors.fill: parent
        color: Theme.bgCard
        radius: Theme.radiusMd
        border.color: Theme.borderSubtle
        border.width: 1
        visible: root.isLoading || root.htmlUrl === ""

        ColumnLayout {
            anchors.centerIn: parent
            spacing: Theme.spaceMd

            // İkon / Yükleniyor Halkası
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 48
                height: 48
                radius: 24
                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12)

                ModernIcon {
                    id: statusIcon
                    anchors.centerIn: parent
                    name: root.isLoading ? "refresh" : "info"
                    size: 22
                    color: Theme.accent
                }

                RotationAnimation on rotation {
                    running: root.isLoading
                    loops: Animation.Infinite
                    from: 0
                    to: 360
                    duration: 1200
                }
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.isLoading ? Strings.loadingStockData : root.emptyTitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.isLoading ? Strings.financialsLoading : root.emptySubtitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
