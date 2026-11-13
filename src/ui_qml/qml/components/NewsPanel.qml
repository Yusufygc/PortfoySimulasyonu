import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

// Genel Bakış haber paneli: "Portföyüm ve İzleme" (şirket) ve "Piyasa ve Global" akışları. newsController ile beslenir.
ModernCard {
    id: root

    readonly property var ctrl: (typeof newsController !== "undefined") ? newsController : null
    property int currentTab: 0   // 0: şirket haberleri, 1: piyasa/global haberleri
    readonly property var activeModel: ctrl ? (currentTab === 0 ? ctrl.companyNews : ctrl.marketNews) : null

    implicitWidth: 380

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Text {
                text: Strings.newsTitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
                color: Theme.textPrimary
                Layout.fillWidth: true
            }

            ModernButton {
                iconName: "refresh"
                variant: "ghost"
                implicitHeight: 28
                enabled: root.ctrl ? !root.ctrl.isLoading : false
                tooltip: Strings.newsRefreshTooltip
                onClicked: root.ctrl.forceRefresh()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs

            Repeater {
                model: [Strings.newsTabCompany, Strings.newsTabMarket]

                // Eşit genişlikli sekme: uzun metin taşmak yerine kısaltılır
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    implicitHeight: 28
                    radius: Theme.radiusSm
                    color: root.currentTab === index ? Theme.accent : (tabMouse.containsMouse ? Theme.bgCardHover : "transparent")

                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceXs
                        anchors.rightMargin: Theme.spaceXs
                        text: modelData
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: root.currentTab === index ? Font.Bold : Font.Normal
                        color: root.currentTab === index ? "#ffffff" : Theme.textPrimary
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    MouseArea {
                        id: tabMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.currentTab = index
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: root.ctrl && root.ctrl.failedSources !== ""
            text: root.ctrl ? Strings.newsFailedPrefix + root.ctrl.failedSources : ""
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontXs
            color: Theme.textWarning
            wrapMode: Text.WordWrap
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: newsList
                anchors.fill: parent
                clip: true
                spacing: Theme.spaceXs
                model: root.activeModel
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ModernScrollBar {}

                delegate: Rectangle {
                    id: row
                    width: newsList.width - 8
                    implicitHeight: rowContent.implicitHeight + 2 * Theme.spaceSm
                    height: implicitHeight
                    radius: Theme.radiusSm
                    color: rowMouse.containsMouse ? Theme.bgCardHover : "transparent"

                    ColumnLayout {
                        id: rowContent
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: 3

                        Text {
                            Layout.fillWidth: true
                            text: model.title
                            textFormat: Text.PlainText  // dış kaynaklı metin zengin metin olarak işlenmez
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                            wrapMode: Text.WordWrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceXs

                            Text {
                                text: model.sourceName
                                textFormat: Text.PlainText  // dış kaynaklı metin zengin metin olarak işlenmez
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                font.weight: Font.Bold
                                color: Theme.textAccent
                            }
                            Text {
                                visible: model.language === "en"
                                text: Strings.newsEnglishBadge
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textMuted
                            }
                            Text {
                                visible: model.symbols !== ""
                                text: model.symbols
                                textFormat: Text.PlainText  // dış kaynaklı metin zengin metin olarak işlenmez
                                font.family: Theme.monoFontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Item { visible: model.symbols === ""; Layout.fillWidth: true }
                            Text {
                                text: model.timeText
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontXs
                                color: Theme.textMuted
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: model.summary !== ""
                            text: model.summary
                            textFormat: Text.PlainText  // dış kaynaklı metin zengin metin olarak işlenmez
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.ctrl.openUrl(model.url)
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                width: parent.width - 2 * Theme.spaceMd
                visible: newsList.count === 0
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: !root.ctrl || root.ctrl.isLoading || !root.ctrl.hasLoaded
                      ? Strings.newsLoading
                      : (root.currentTab === 0 ? Strings.newsEmptyCompany : Strings.newsEmptyMarket)
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
            }
        }
    }
}
