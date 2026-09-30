import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    signal newPortfolioRequested()
    signal editPortfolioRequested(int portfolioId, string name, string desc)

    color: Theme.bgCard
    radius: Theme.radiusMd
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        spacing: Theme.spaceSm

        // Üst Başlık & Yeni Butonu
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            ModernIcon {
                iconSource: Icons.get("layers")
                iconColor: Theme.accent
                width: 18
                height: 18
            }

            Text {
                text: Strings.portfolioMyPortfolios
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                font.letterSpacing: 0.5
                Layout.fillWidth: true
            }

            Rectangle {
                width: 28
                height: 28
                radius: Theme.radiusSm
                color: btnNewMouse.containsMouse ? Theme.accentHover : Theme.accent

                ModernIcon {
                    anchors.centerIn: parent
                    iconSource: Icons.get("plus")
                    iconColor: Theme.textInverse
                    width: 14
                    height: 14
                }

                MouseArea {
                    id: btnNewMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.newPortfolioRequested()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderSubtle
        }

        // Portföy Listesi
        ListView {
            id: portfolioListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: Theme.spaceXs
            model: portfolioController.portfolioList

            ScrollBar.vertical: ModernScrollBar {}

            delegate: Rectangle {
                id: itemDelegate
                width: portfolioListView.width
                height: modelData.description ? 62 : 46
                radius: Theme.radiusSm

                readonly property bool isSelected: portfolioController.currentPortfolioId === modelData.portfolioId

                color: {
                    if (isSelected) return Theme.accentSoft
                    if (itemMouse.containsMouse) return Theme.bgCardHover
                    return Theme.bgSecondary
                }

                border.color: isSelected ? Theme.accent : Theme.borderSubtle
                border.width: 1

                // Sol seçim gösterge çizgisi
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 3
                    radius: 2
                    color: Theme.accent
                    visible: itemDelegate.isSelected
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceSm + (itemDelegate.isSelected ? 4 : 0)
                    anchors.rightMargin: Theme.spaceSm
                    spacing: Theme.spaceSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            spacing: Theme.spaceSm
                            Layout.fillWidth: true

                            Text {
                                text: modelData.name
                                color: itemDelegate.isSelected ? Theme.accent : Theme.textPrimary
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.weight: itemDelegate.isSelected ? Font.DemiBold : Font.Normal
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            // Pozisyon adedi rozeti
                            Rectangle {
                                height: 18
                                width: badgeText.width + 10
                                radius: Theme.radiusFull
                                color: itemDelegate.isSelected ? Theme.accent : Theme.borderSubtle

                                Text {
                                    id: badgeText
                                    anchors.centerIn: parent
                                    text: modelData.positionCount + Strings.portfolioPositionsSuffix
                                    color: itemDelegate.isSelected ? Theme.textInverse : Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontXs
                                }
                            }
                        }

                        Text {
                            text: modelData.description || ""
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontXs
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            visible: modelData.description !== ""
                        }
                    }

                    // Düzenle & Sil Mini Butonları
                    RowLayout {
                        spacing: 2
                        visible: itemMouse.containsMouse || itemDelegate.isSelected

                        // Düzenle
                        Rectangle {
                            width: 24
                            height: 24
                            radius: Theme.radiusXs
                            color: btnEditMouse.containsMouse ? Theme.bgCardHover : "transparent"

                            ModernIcon {
                                anchors.centerIn: parent
                                iconSource: Icons.get("edit")
                                iconColor: Theme.textSecondary
                                width: 12
                                height: 12
                            }

                            MouseArea {
                                id: btnEditMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.editPortfolioRequested(
                                    modelData.portfolioId,
                                    modelData.name,
                                    modelData.description || ""
                                )
                            }
                        }

                        // Sil
                        Rectangle {
                            width: 24
                            height: 24
                            radius: Theme.radiusXs
                            color: btnDeleteMouse.containsMouse ? Theme.bearRedSoft : "transparent"

                            ModernIcon {
                                anchors.centerIn: parent
                                iconSource: Icons.get("trash")
                                iconColor: btnDeleteMouse.containsMouse ? Theme.bearRed : Theme.textMuted
                                width: 12
                                height: 12
                            }

                            MouseArea {
                                id: btnDeleteMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: portfolioController.deletePortfolio(modelData.portfolioId)
                            }
                        }
                    }
                }

                MouseArea {
                    id: itemMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.LeftButton
                    z: -1
                    onClicked: portfolioController.selectPortfolio(modelData.portfolioId)
                }
            }
        }

        // Boş Durum (Portföy Yoksa)
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: portfolioController.portfolioList.length === 0
            spacing: Theme.spaceSm

            Item { Layout.fillHeight: true }

            ModernIcon {
                Layout.alignment: Qt.AlignHCenter
                iconSource: Icons.get("portfolio")
                iconColor: Theme.textMuted
                width: 36
                height: 36
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: Strings.portfolioNoPortfoliosTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: Font.DemiBold
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.maximumWidth: 220
                text: Strings.portfolioNoPortfoliosSubtitle
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 130
                height: 34
                radius: Theme.radiusSm
                color: btnEmptyCreateMouse.containsMouse ? Theme.accentHover : Theme.accent

                Text {
                    anchors.centerIn: parent
                    text: Strings.portfolioBtnNew
                    color: Theme.textInverse
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    id: btnEmptyCreateMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.newPortfolioRequested()
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
