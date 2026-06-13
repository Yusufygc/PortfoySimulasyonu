# src/ui/widgets/dashboard/dialogs/corporate_action_dialog.py
"""
Bedelli / Bedelsiz Sermaye Artırımı giriş diyaloğu.

Kullanıcı:
  - İşlem türünü (BEDELLI / BEDELSİZ) seçer
  - Artırım oranını girer (% olarak)
  - Ex-date'i girer
  - Bedelli için rüçhan hakkı kullanım fiyatını girer
  - Canlı ön izleme ile etkiyi görür (yeni lot sayısı, yeni ort. maliyet, teorik baz fiyat)
"""

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from decimal import Decimal
from typing import Optional, Dict, Any

from src.qt_compat.qtcore import Qt, QDate
from src.qt_compat.qtwidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFormLayout,
    QRadioButton,
    QButtonGroup,
    QDoubleSpinBox,
    QDateEdit,
    QLineEdit,
    QPushButton,
    QFrame,
    QGroupBox,
)

from src.ui.formatters import display_ticker
from src.ui.widgets.dialog_behavior import configure_dialog_behavior
from src.ui.widgets.shared import CurrencySpinBox


class CorporateActionDialog(QDialog):
    """
    Sermaye artırımı giriş ve ön izleme diyaloğu.

    Parametreler:
      ticker          : Hisse kodu (görüntüleme için)
      stock_id        : Hisse ID
      current_qty     : Mevcut lot sayısı
      avg_cost        : Mevcut ortalama maliyet
      total_cost      : Toplam maliyet (ort. maliyet × lot)
      current_price   : Anlık fiyat (None ise teorik fiyat hesaplanamaz)
    """

    def __init__(
        self,
        ticker: str,
        stock_id: int,
        current_qty: int,
        avg_cost: Optional[Decimal],
        total_cost: Decimal,
        current_price: Optional[Decimal] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self._ticker = ticker
        self._display_ticker = display_ticker(ticker)
        self._stock_id = stock_id
        self._current_qty = current_qty
        self._avg_cost = avg_cost or Decimal("0")
        self._total_cost = total_cost
        self._current_price = current_price

        self.setWindowTitle(L10N.SERMAYE_ARTIRIMI_TMPL.format(ticker=self._display_ticker))
        self.setMinimumWidth(440)
        self.setModal(True)
        self.setProperty("cssClass", "dialogContainer")

        self._init_ui()
        configure_dialog_behavior(self, self._btn_confirm, self.accept)
        self._update_preview()

    # ══════════════════════════════════════════════════════════
    #  UI KURULUMU
    # ══════════════════════════════════════════════════════════

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── Başlık / Hisse Bilgisi ──────────────────────────
        title = QLabel(L10N.SERMAYE_ARTIRIMI)
        title.setProperty("cssClass", "dialogHeaderTitle")
        layout.addWidget(title)

        info_frame = QFrame()
        info_frame.setProperty("cssClass", "dialogInfoFrame")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setSpacing(24)

        def _info_col(lbl_text, val_text):
            col = QVBoxLayout()
            lbl = QLabel(lbl_text)
            lbl.setProperty("cssClass", "dialogFieldLabel")
            val = QLabel(val_text)
            val.setProperty("cssClass", "dialogFieldValue")
            col.addWidget(lbl)
            col.addWidget(val)
            return col

        price_txt = f"{self._current_price:,.4f} TL" if self._current_price else "—"
        info_layout.addLayout(_info_col("Hisse", self._display_ticker))
        info_layout.addLayout(_info_col(L10N.MEVCUT_LOT, f"{self._current_qty:,}"))
        info_layout.addLayout(_info_col(L10N.ORT_MALIYET, f"{self._avg_cost:,.4f} TL"))
        info_layout.addLayout(_info_col(L10N.GUNCEL_FIYAT, price_txt))
        info_layout.addStretch()
        layout.addWidget(info_frame)

        # ── Giriş Formu ─────────────────────────────────────
        form_group = QGroupBox(L10N.ISLEM_PARAMETRELERI)
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(12, 14, 12, 12)

        # İşlem türü
        type_layout = QHBoxLayout()
        self._radio_bedelsiz = QRadioButton(L10N.BEDELSIZ)
        self._radio_bedelli = QRadioButton(L10N.BEDELLI)
        self._radio_bedelsiz.setChecked(True)
        self._type_group = QButtonGroup(self)
        self._type_group.addButton(self._radio_bedelsiz, 0)
        self._type_group.addButton(self._radio_bedelli, 1)
        self._type_group.buttonClicked.connect(self._on_type_changed)
        type_layout.addWidget(self._radio_bedelsiz)
        type_layout.addWidget(self._radio_bedelli)
        type_layout.addStretch()
        form_layout.addRow(L10N.ISLEM_TURU_1, type_layout)

        # Artırım oranı (%)
        self._spin_ratio = QDoubleSpinBox()
        self._spin_ratio.setRange(0.01, 10000.0)
        self._spin_ratio.setValue(50.0)
        self._spin_ratio.setDecimals(2)
        self._spin_ratio.setSuffix("  %")
        self._spin_ratio.setProperty("cssClass", "tradeInputNormal")
        self._spin_ratio.valueChanged.connect(self._update_preview)
        form_layout.addRow(L10N.ARTIRIM_ORANI_1, self._spin_ratio)

        # Ex-date
        self._date_ex = QDateEdit(QDate.currentDate())
        self._date_ex.setCalendarPopup(True)
        self._date_ex.setDisplayFormat("dd.MM.yyyy")
        self._date_ex.setProperty("cssClass", "tradeInputNormal")
        form_layout.addRow(L10N.EXDATE_BAZ_FIYAT_GUNU, self._date_ex)

        # ── Bedelli alanları (gizli/görünür) ────────────────
        self._lbl_sub_price = QLabel(L10N.KULLANIM_FIYATI_RUCHAN)
        self._spin_sub_price = CurrencySpinBox()
        self._spin_sub_price.setRange(0.0001, 10000.0)
        self._spin_sub_price.setValue(1.00)
        self._spin_sub_price.setDecimals(4)
        self._spin_sub_price.setSuffix("  TL")
        self._spin_sub_price.setProperty("cssClass", "tradeInputNormal")
        self._spin_sub_price.valueChanged.connect(self._update_preview)
        form_layout.addRow(self._lbl_sub_price, self._spin_sub_price)

        # Not (opsiyonel)
        self._edit_notes = QLineEdit()
        self._edit_notes.setPlaceholderText(L10N.OPSIYONEL_ACIKLAMA)
        self._edit_notes.setProperty("cssClass", "tradeInputNormal")
        form_layout.addRow(L10N.NOT, self._edit_notes)

        layout.addWidget(form_group)

        # ── Ön İzleme ────────────────────────────────────────
        preview_group = QGroupBox(L10N.ON_IZLEME)
        preview_layout = QFormLayout(preview_group)
        preview_layout.setSpacing(8)
        preview_layout.setContentsMargins(12, 14, 12, 12)

        self._lbl_new_shares = QLabel("—")
        self._lbl_total_qty = QLabel("—")
        self._lbl_new_avg = QLabel("—")
        self._lbl_capital_spent = QLabel("—")
        self._lbl_theoretical = QLabel("—")

        for lbl in (self._lbl_new_shares, self._lbl_total_qty,
                    self._lbl_new_avg, self._lbl_capital_spent, self._lbl_theoretical):
            lbl.setProperty("cssClass", "dialogFieldValue")

        preview_layout.addRow(L10N.YENI_HISSE_ADEDI, self._lbl_new_shares)
        preview_layout.addRow(L10N.TOPLAM_LOT_1, self._lbl_total_qty)
        preview_layout.addRow(L10N.YENI_ORT_MALIYET_1, self._lbl_new_avg)

        self._row_capital_lbl = QLabel(L10N.SERMAYE_KULLANIMI)
        self._row_capital_lbl.setProperty("cssClass", "dialogFieldLabel")
        preview_layout.addRow(self._row_capital_lbl, self._lbl_capital_spent)

        preview_layout.addRow(L10N.TEORIK_BAZ_FIYAT, self._lbl_theoretical)
        layout.addWidget(preview_group)

        # Tüm widget'lar tanımlandıktan sonra başlangıç görünürlüğünü ayarla
        self._set_bedelli_fields_visible(False)

        # ── Bilgi notu ────────────────────────────────────────
        note = QLabel(
            L10N.UYGULAMA_SONRASI_GECMIS_FIYATLAR_YFINANCEDEN +
            L10N.RETROAKTIF_DUZELTME_BU_ISLEM_BIRKAC
        )
        note.setWordWrap(True)
        note.setProperty("cssClass", "pageDescription")
        layout.addWidget(note)

        # ── Butonlar ──────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(L10N.CANCEL)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setProperty("cssClass", "secondaryButton")

        self._btn_confirm = QPushButton(L10N.UYGULA)
        self._btn_confirm.clicked.connect(self.accept)
        self._btn_confirm.setProperty("cssClass", "tradeConfirmBuyBtn")
        self._btn_confirm.setDefault(True)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self._btn_confirm)
        layout.addLayout(btn_layout)

    # ══════════════════════════════════════════════════════════
    #  EVENT HANDLERS
    # ══════════════════════════════════════════════════════════

    def _on_type_changed(self, btn):
        is_bedelli = self._type_group.checkedId() == 1
        self._set_bedelli_fields_visible(is_bedelli)
        self._update_preview()

    def _set_bedelli_fields_visible(self, visible: bool):
        self._lbl_sub_price.setVisible(visible)
        self._spin_sub_price.setVisible(visible)
        self._row_capital_lbl.setVisible(visible)
        self._lbl_capital_spent.setVisible(visible)

    # ══════════════════════════════════════════════════════════
    #  CANLI ÖN İZLEME
    # ══════════════════════════════════════════════════════════

    def _update_preview(self):
        ratio = Decimal(str(self._spin_ratio.value())) / Decimal("100")
        new_shares = int(Decimal(str(self._current_qty)) * ratio)  # floor (BİST kuralı)
        total_qty = self._current_qty + new_shares

        self._lbl_new_shares.setText(f"+ {new_shares:,} lot")
        self._lbl_total_qty.setText(f"{total_qty:,} lot")

        is_bedelli = self._type_group.checkedId() == 1

        if total_qty > 0:
            if is_bedelli:
                sub_price = self._spin_sub_price.decimal_value()
                capital_spent = sub_price * Decimal(str(new_shares))
                new_total_cost = self._total_cost + capital_spent
                new_avg = new_total_cost / Decimal(str(total_qty))
                self._lbl_capital_spent.setText(f"{capital_spent:,.2f} TL")
            else:
                new_avg = self._total_cost / Decimal(str(total_qty))

            self._lbl_new_avg.setText(f"{new_avg:,.4f} TL")
        else:
            self._lbl_new_avg.setText("—")

        # Teorik baz fiyat
        if self._current_price:
            p = self._current_price
            if is_bedelli:
                sub_price = self._spin_sub_price.decimal_value()
                theoretical = (p + ratio * sub_price) / (Decimal("1") + ratio)
            else:
                theoretical = p / (Decimal("1") + ratio)
            self._lbl_theoretical.setText(f"{theoretical:,.4f} TL")
        else:
            self._lbl_theoretical.setText(L10N.FIYAT_VERISI_YOK)

        # Yeterli lot yoksa butonu devre dışı bırak
        self._btn_confirm.setEnabled(new_shares > 0)
        if new_shares <= 0:
            self._lbl_new_shares.setText(L10N.UYARI_MEVCUT_LOT_YETERSIZ_0)

    # ══════════════════════════════════════════════════════════
    #  SONUÇ
    # ══════════════════════════════════════════════════════════

    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Dialog Accepted durumunda çağrılır.
        Dönüş: dict veya None.
        """
        ratio_pct = Decimal(str(self._spin_ratio.value()))
        ratio = ratio_pct / Decimal("100")
        is_bedelli = self._type_group.checkedId() == 1

        qdate = self._date_ex.date()
        from datetime import date
        ex_date = date(qdate.year(), qdate.month(), qdate.day())

        result = {
            "action_type": "BEDELLI" if is_bedelli else "BEDELSIZ",
            "stock_id": self._stock_id,
            "ticker": self._ticker,
            "ratio": ratio,
            "ex_date": ex_date,
            "notes": self._edit_notes.text().strip() or None,
        }

        if is_bedelli:
            result["subscription_price"] = self._spin_sub_price.decimal_value()

        return result
