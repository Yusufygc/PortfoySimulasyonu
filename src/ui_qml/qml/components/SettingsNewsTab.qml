import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"

// Ayarlar > Haber Kaynakları: kaynak aç/kapa, özel RSS ekleme, bağlantı testi ve yenileme aralığı.
ColumnLayout {
    id: root

    readonly property bool hasController: typeof newsSettingsController !== "undefined"
    readonly property var sources: hasController ? newsSettingsController.sources : []

    // Ayarlar ekranındaki global toast'a iletilir
    signal notify(bool success, string message)

    spacing: 16

    Connections {
        target: root.hasController ? newsSettingsController : null
        function onNotify(success, message) { root.notify(success, message) }
    }

    // Kaynak satırı: ad, açıklama, durum, aç/kapa anahtarı, test ve (özel kaynaklarda) silme
    component SourceRow: ColumnLayout {
        id: row
        property var source: ({})
        Layout.fillWidth: true
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Switch {
                checked: row.source.enabled
                onToggled: newsSettingsController.setSourceEnabled(row.source.sourceId, checked)
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                RowLayout {
                    spacing: Theme.spaceXs
                    Text {
                        text: row.source.name
                        color: Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        font.weight: Font.DemiBold
                    }
                    Text {
                        visible: row.source.language === "en"
                        text: Strings.newsEnglishBadge
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }
                    Text {
                        visible: row.source.isCustom
                        text: Strings.newsSetCustomBadge
                        color: Theme.accent
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontXs
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: row.source.description !== ""
                    text: row.source.description
                    color: Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    elide: Text.ElideMiddle
                }
                Text {
                    Layout.fillWidth: true
                    text: row.source.statusText
                    color: row.source.hasError ? Theme.bearRed : Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontXs
                    wrapMode: Text.WordWrap
                }
            }

            ModernButton {
                text: Strings.newsSetTest
                variant: "secondary"
                implicitHeight: 28
                enabled: !newsSettingsController.isTesting
                onClicked: newsSettingsController.testSource(row.source.sourceId)
            }
            ModernButton {
                visible: row.source.isCustom
                text: Strings.newsSetRemove
                variant: "danger"
                implicitHeight: 28
                onClicked: newsSettingsController.removeSource(row.source.sourceId)
            }
        }

        RowLayout {
            visible: row.source.isKap === true
            Layout.leftMargin: 40
            spacing: Theme.spaceSm

            Switch {
                checked: row.source.massNotices
                onToggled: newsSettingsController.setMassNotices(checked)
            }
            Text {
                text: Strings.newsSetMassNotices
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
            }
        }
    }

    // Şirket ve varlık haberi kaynakları
    ModernCard {
        Layout.fillWidth: true
        implicitHeight: companyColumn.implicitHeight + Theme.spaceLg * 2

        ColumnLayout {
            id: companyColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceSm

            Text {
                text: Strings.newsSetTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
            }
            Text {
                text: Strings.newsSetDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Text {
                text: Strings.newsSetCompanyGroup
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.Bold
                Layout.topMargin: Theme.spaceSm
            }
            Text {
                text: Strings.newsSetCompanyNote
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontXs
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Repeater {
                model: root.sources.filter(function (s) { return s.isCompany })
                SourceRow { source: modelData }
            }
        }
    }

    // Piyasa ve global genel akışlar
    ModernCard {
        Layout.fillWidth: true
        implicitHeight: marketColumn.implicitHeight + Theme.spaceLg * 2

        ColumnLayout {
            id: marketColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceSm

            Text {
                text: Strings.newsSetMarketGroup
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
            }

            Repeater {
                model: root.sources.filter(function (s) { return !s.isCompany })
                SourceRow { source: modelData }
            }
        }
    }

    // Özel RSS beslemesi
    ModernCard {
        Layout.fillWidth: true
        implicitHeight: addColumn.implicitHeight + Theme.spaceLg * 2

        ColumnLayout {
            id: addColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceSm

            Text {
                text: Strings.newsSetAddTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
            }
            Text {
                text: Strings.newsSetAddDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                ModernInput {
                    id: feedName
                    width: 200
                    placeholder: Strings.newsSetName
                }
                ModernInput {
                    id: feedUrl
                    width: 320
                    placeholder: Strings.newsSetUrl
                }
                ModernComboBox {
                    id: feedLang
                    implicitWidth: 130
                    model: [Strings.newsSetLangTr, Strings.newsSetLangEn]
                }
            }

            RowLayout {
                spacing: Theme.spaceSm
                ModernButton {
                    text: Strings.newsSetTest
                    variant: "secondary"
                    enabled: root.hasController && !newsSettingsController.isTesting && feedUrl.text.trim() !== ""
                    onClicked: newsSettingsController.testNewUrl(feedUrl.text)
                }
                ModernButton {
                    text: Strings.newsSetAdd
                    iconName: "plus"
                    enabled: root.hasController && feedName.text.trim() !== "" && feedUrl.text.trim() !== ""
                    onClicked: {
                        newsSettingsController.addRssFeed(feedName.text, feedUrl.text, feedLang.currentIndex === 1 ? "en" : "tr")
                        feedName.clear()
                        feedUrl.clear()
                    }
                }
            }
        }
    }

    // Yenileme aralığı
    ModernCard {
        Layout.fillWidth: true
        implicitHeight: intervalColumn.implicitHeight + Theme.spaceLg * 2

        ColumnLayout {
            id: intervalColumn
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.spaceSm

            Text {
                text: Strings.newsSetIntervalTitle
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontMd
                font.weight: Font.Bold
            }
            Text {
                text: Strings.newsSetIntervalDesc
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            ModernComboBox {
                implicitWidth: 120
                model: root.hasController ? newsSettingsController.refreshOptions.map(function (m) { return m + Strings.newsSetMinuteSuffix }) : []
                currentIndex: root.hasController ? newsSettingsController.refreshOptions.indexOf(newsSettingsController.refreshMinutes) : 0
                onActivated: newsSettingsController.setRefreshMinutes(newsSettingsController.refreshOptions[currentIndex])
            }
        }
    }
}
