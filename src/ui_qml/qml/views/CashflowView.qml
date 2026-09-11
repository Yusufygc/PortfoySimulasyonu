import QtQuick
import QtQuick.Controls

// CashflowView (bkz. plan §7.3 madde 8, d6) — mevcut `PlanningPage` (bütçe +
// hedef takibi) + `CashMovementService` (sermaye ekleme/çekme) birleşik
// karşılığı, 3 sekme: Bütçe / Hedefler / Nakit Hareketleri. Veri: context
// property `cashflowController` (bkz.
// src/ui_qml/controllers/cashflow_controller.py).
//
// Not (plan'dan dürüst sapma): "Temettü" akışı burada YOK — backend'de nakit
// temettüsü modelleyen bir domain/servis kaydı yok (`CorporateAction` sadece
// bedelli/bedelsiz sermaye artırımını modelliyor), icat edilmedi. Hedef
// DÜZENLEME (isim/tutar/vade değişikliği) de v1 kapsamına alınmadı — sadece
// ekle/katkı/sil.
//
// Not: Layout `headerColumn` (sekme çubuğu dahil, otomatik yükseklik) +
// `tabContent` (anchors ile kalan alanı dolduran, her sekme kendi Flickable'ı)
// deseni — Stock360View'daki NaN-yükseklik hatasından ders alınarak.
Item {
    id: root
    anchors.fill: parent

    readonly property color colorAccent: "#3B82F6"
    readonly property color colorProfit: "#10B981"
    readonly property color colorLoss: "#EF4444"
    readonly property color colorMuted: "#9CA3AF"

    function fmtMoney(value) { return value.toLocaleString(Qt.locale("tr_TR"), 'f', 2) }

    Column {
        id: headerColumn
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 10

        Text { text: "Nakit Akış & Bütçe"; color: "#E5E7EB"; font.pixelSize: 18; font.bold: true }

        TabBar {
            id: tabBar
            objectName: "tabBar"
            width: parent.width
            background: Rectangle { color: "#151D2C" }

            TabButton { text: "Bütçe" }
            TabButton { text: "Hedefler" }
            TabButton { text: "Nakit Hareketleri" }
        }
    }

    Item {
        id: tabContent
        objectName: "tabContent"
        anchors.top: headerColumn.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.topMargin: 14
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        anchors.bottomMargin: 20

        // ================= Sekme 1: Bütçe ================= //
        Flickable {
            visible: tabBar.currentIndex === 0
            anchors.fill: parent
            contentHeight: budgetColumn.height
            clip: true

            Column {
                id: budgetColumn
                width: parent.width
                spacing: 14

                Row {
                    spacing: 12
                    Text { text: "Ay:"; color: root.colorMuted; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12 }
                    ComboBox {
                        width: 140
                        model: cashflowController.monthKeys
                        onActivated: cashflowController.selectMonth(cashflowController.monthKeys[currentIndex])
                    }
                    Text { text: "Tasarruf Hedefi:"; color: root.colorMuted; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12 }
                    TextField {
                        width: 120
                        text: cashflowController.savingsTarget.toString()
                        validator: DoubleValidator { bottom: 0 }
                        onEditingFinished: cashflowController.setSavingsTarget(parseFloat(text) || 0)
                    }
                    Button { text: "Bütçeyi Kaydet"; onClicked: cashflowController.saveBudget() }
                }

                Text {
                    visible: cashflowController.budgetError !== ""
                    text: cashflowController.budgetError
                    color: root.colorLoss
                    font.pixelSize: 11
                }

                Row {
                    spacing: 8
                    ComboBox { id: newItemType; width: 90; model: ["Gelir", "Gider"] }
                    TextField { id: newItemName; width: 160; placeholderText: "Kalem adı (örn. Kira)" }
                    TextField {
                        id: newItemAmount
                        width: 110
                        placeholderText: "Tutar"
                        validator: DoubleValidator { bottom: 0 }
                    }
                    Button {
                        text: "Ekle"
                        onClicked: {
                            var amount = parseFloat(newItemAmount.text)
                            if (isNaN(amount) || amount <= 0 || newItemName.text.trim() === "") return
                            cashflowController.addBudgetItem(newItemType.currentIndex === 0 ? "income" : "expense", newItemName.text, amount)
                            newItemName.text = ""
                            newItemAmount.text = ""
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 40 + cashflowController.budgetItemNames.length * 30
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 4

                        Repeater {
                            model: cashflowController.budgetItemNames.length
                            delegate: Row {
                                spacing: 16
                                Rectangle {
                                    width: 50; height: 18; radius: 4
                                    color: cashflowController.budgetItemTypes[index] === "income" ? root.colorProfit : root.colorLoss
                                    Text {
                                        anchors.centerIn: parent
                                        text: cashflowController.budgetItemTypes[index] === "income" ? "Gelir" : "Gider"
                                        color: "#0B0F19"; font.pixelSize: 9; font.bold: true
                                    }
                                }
                                Text { width: 140; text: cashflowController.budgetItemNames[index]; color: "#E5E7EB"; font.pixelSize: 12 }
                                Text { width: 100; text: root.fmtMoney(cashflowController.budgetItemAmounts[index]) + " ₺"; color: root.colorMuted; font.pixelSize: 12 }
                                Button {
                                    text: "Pinle"
                                    onClicked: cashflowController.togglePinBudgetItem(
                                        cashflowController.budgetItemTypes[index], cashflowController.budgetItemNames[index],
                                        cashflowController.budgetItemAmounts[index], true)
                                }
                                Button { text: "Sil"; onClicked: cashflowController.removeBudgetItem(index) }
                            }
                        }

                        Text {
                            visible: cashflowController.budgetItemNames.length === 0
                            text: "Bu ay için henüz kalem yok."
                            color: root.colorMuted
                            font.pixelSize: 11
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 120
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 4

                        Row {
                            spacing: 24
                            Text { text: "Toplam Gelir: " + root.fmtMoney(cashflowController.totalIncome) + " ₺"; color: root.colorProfit; font.pixelSize: 12 }
                            Text { text: "Toplam Gider: " + root.fmtMoney(cashflowController.totalExpense) + " ₺"; color: root.colorLoss; font.pixelSize: 12 }
                            Text { text: "Net: " + root.fmtMoney(cashflowController.netSavingsPotential) + " ₺"; color: "#E5E7EB"; font.pixelSize: 12; font.bold: true }
                        }
                        Text {
                            width: parent.width
                            text: cashflowController.budgetStatusMessage
                            color: root.colorMuted
                            wrapMode: Text.WordWrap
                            font.pixelSize: 11
                        }
                    }
                }

                Text {
                    visible: cashflowController.pinnedItemNames.length > 0
                    width: parent.width
                    text: "Şablonlar: " + cashflowController.pinnedItemNames.join(", ")
                    color: root.colorMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }

        // ================= Sekme 2: Hedefler ================= //
        Flickable {
            visible: tabBar.currentIndex === 1
            anchors.fill: parent
            contentHeight: goalsColumn.height
            clip: true

            Column {
                id: goalsColumn
                width: parent.width
                spacing: 14

                Row {
                    spacing: 8
                    TextField { id: goalName; width: 140; placeholderText: "Hedef adı" }
                    TextField { id: goalTarget; width: 110; placeholderText: "Hedef Tutar"; validator: DoubleValidator { bottom: 0 } }
                    TextField { id: goalDeadline; width: 110; placeholderText: "Vade (YYYY-MM-DD)" }
                    ComboBox { id: goalPriority; width: 100; model: ["LOW", "MEDIUM", "HIGH"]; currentIndex: 1 }
                    Button {
                        text: "Hedef Ekle"
                        onClicked: {
                            var target = parseFloat(goalTarget.text)
                            if (goalName.text.trim() === "" || isNaN(target) || target <= 0) return
                            cashflowController.addGoal(goalName.text, target, goalDeadline.text, goalPriority.currentText)
                            goalName.text = ""; goalTarget.text = ""; goalDeadline.text = ""
                        }
                    }
                }

                Text {
                    visible: cashflowController.goalError !== ""
                    text: cashflowController.goalError
                    color: root.colorLoss
                    font.pixelSize: 11
                }

                Repeater {
                    model: cashflowController.goalNames.length
                    delegate: Rectangle {
                        width: goalsColumn.width
                        height: 90
                        radius: 12
                        color: "#151D2C"
                        border.color: "#26354A"
                        border.width: 1

                        Column {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 14
                            spacing: 6

                            Row {
                                spacing: 16
                                Text { text: cashflowController.goalNames[index]; color: "#E5E7EB"; font.bold: true; font.pixelSize: 13 }
                                Text {
                                    text: cashflowController.goalStatuses[index] === "COMPLETED" ? "Tamamlandı" : cashflowController.goalPriorities[index]
                                    color: root.colorMuted
                                    font.pixelSize: 11
                                }
                                Text { text: "Vade: " + (cashflowController.goalDeadlines[index] || "-"); color: root.colorMuted; font.pixelSize: 11 }
                            }

                            Rectangle {
                                width: parent.width; height: 6; radius: 3; color: "#26354A"
                                Rectangle {
                                    width: parent.width * Math.min(cashflowController.goalProgressPct[index] / 100.0, 1.0)
                                    height: parent.height; radius: 3; color: root.colorAccent
                                }
                            }

                            Row {
                                spacing: 16
                                Text {
                                    text: root.fmtMoney(cashflowController.goalCurrentAmounts[index]) + " / " + root.fmtMoney(cashflowController.goalTargetAmounts[index]) + " ₺"
                                    color: root.colorMuted
                                    font.pixelSize: 11
                                }
                                TextField {
                                    id: contribAmount
                                    width: 90
                                    placeholderText: "Katkı"
                                    validator: DoubleValidator { bottom: 0 }
                                }
                                Button {
                                    text: "Katkı Ekle"
                                    onClicked: {
                                        var amount = parseFloat(contribAmount.text)
                                        if (isNaN(amount) || amount <= 0) return
                                        cashflowController.contributeToGoal(cashflowController.goalIds[index], amount)
                                        contribAmount.text = ""
                                    }
                                }
                                Button {
                                    text: "Sil"
                                    onClicked: cashflowController.deleteGoal(cashflowController.goalIds[index])
                                }
                            }
                        }
                    }
                }

                Text {
                    visible: cashflowController.goalNames.length === 0
                    text: "Henüz bir hedef eklenmedi."
                    color: root.colorMuted
                    font.pixelSize: 11
                }

                Rectangle {
                    width: parent.width
                    height: 100
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 6

                        Row {
                            spacing: 12
                            Text { text: "Fizibilite Analizi"; color: root.colorMuted; font.pixelSize: 12 }
                            Button { text: "Analiz Et"; onClicked: cashflowController.runFeasibilityAnalysis() }
                        }
                        Text {
                            visible: cashflowController.feasibilityStatus !== ""
                            text: cashflowController.feasibilityStatus + " — Aylık Güç: " + root.fmtMoney(cashflowController.feasibilityMonthlyPower)
                                + " ₺ / İhtiyaç: " + root.fmtMoney(cashflowController.feasibilityTotalMonthlyNeed) + " ₺"
                            color: "#E5E7EB"
                            font.pixelSize: 11
                        }
                        Text {
                            visible: cashflowController.feasibilityMessage !== ""
                            text: cashflowController.feasibilityMessage
                            color: root.colorMuted
                            wrapMode: Text.WordWrap
                            width: parent.width
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }

        // ================= Sekme 3: Nakit Hareketleri ================= //
        Flickable {
            visible: tabBar.currentIndex === 2
            anchors.fill: parent
            contentHeight: cashColumn.height
            clip: true

            Column {
                id: cashColumn
                width: parent.width
                spacing: 14

                Rectangle {
                    width: 240
                    height: 70
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1
                    Column {
                        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 14; spacing: 4
                        Text { text: "Nakit Bakiyesi"; color: root.colorMuted; font.pixelSize: 11 }
                        Text { text: root.fmtMoney(cashflowController.cashBalance) + " ₺"; color: "#E5E7EB"; font.pixelSize: 16; font.bold: true }
                    }
                }

                Row {
                    spacing: 8
                    TextField { id: movementAmount; width: 110; placeholderText: "Tutar"; validator: DoubleValidator { bottom: 0 } }
                    TextField { id: movementNotes; width: 180; placeholderText: "Not (opsiyonel)" }
                    Button {
                        text: "Yatır"
                        onClicked: {
                            var amount = parseFloat(movementAmount.text)
                            if (isNaN(amount) || amount <= 0) return
                            cashflowController.addDeposit(amount, movementNotes.text)
                            movementAmount.text = ""; movementNotes.text = ""
                        }
                    }
                    Button {
                        text: "Çek"
                        onClicked: {
                            var amount = parseFloat(movementAmount.text)
                            if (isNaN(amount) || amount <= 0) return
                            cashflowController.addWithdraw(amount, movementNotes.text)
                            movementAmount.text = ""; movementNotes.text = ""
                        }
                    }
                }

                Text {
                    visible: cashflowController.cashMovementError !== ""
                    text: cashflowController.cashMovementError
                    color: root.colorLoss
                    font.pixelSize: 11
                }

                Rectangle {
                    width: parent.width
                    height: 40 + cashflowController.movementDates.length * 28
                    radius: 12
                    color: "#151D2C"
                    border.color: "#26354A"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 4

                        Repeater {
                            model: cashflowController.movementDates.length
                            delegate: Row {
                                spacing: 16
                                Text { width: 90; text: cashflowController.movementDates[index]; color: root.colorMuted; font.pixelSize: 11 }
                                Rectangle {
                                    width: 60; height: 18; radius: 4
                                    color: cashflowController.movementTypes[index] === "DEPOSIT" ? root.colorProfit : root.colorLoss
                                    Text {
                                        anchors.centerIn: parent
                                        text: cashflowController.movementTypes[index] === "DEPOSIT" ? "Yatırım" : "Çekim"
                                        color: "#0B0F19"; font.pixelSize: 9; font.bold: true
                                    }
                                }
                                Text { width: 100; text: root.fmtMoney(cashflowController.movementAmounts[index]) + " ₺"; color: "#E5E7EB"; font.pixelSize: 12 }
                                Text { text: cashflowController.movementNotes[index]; color: root.colorMuted; font.pixelSize: 11 }
                            }
                        }

                        Text {
                            visible: cashflowController.movementDates.length === 0
                            text: "Henüz nakit hareketi yok."
                            color: root.colorMuted
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }
    }
}
