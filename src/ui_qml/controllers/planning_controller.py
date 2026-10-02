"""
PlanningController — Finansal Planlama, Bütçe, Hedefler ve DCA Simülasyonu QML controller'ı.

Sorumluluk:
- Bütçe Yönetimi (aylık gelir/gider takibi, tasarruf potansiyeli, kalem ekleme/çıkarma)
- Finansal Hedefler (hedef CRUD, ilerleme, katkı ekleme, fizibilite analizi)
- Kademeli Alım (DCA) Backtest Simülasyonu (düzenli alım senaryosu, geçmiş getiri, portföy değeri)
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from src.domain.models.budget import Budget, BudgetItem
from src.domain.models.financial_goal import FinancialGoal, GoalStatus

logger = logging.getLogger(__name__)

_JS_DIR = Path(__file__).resolve().parent.parent / "assets" / "js"
_LW_CHARTS_JS: str = ""


def _load_embedded_scripts() -> None:
    global _LW_CHARTS_JS
    if not _LW_CHARTS_JS:
        lw_file = _JS_DIR / "lightweight-charts.standalone.production.js"
        if lw_file.exists():
            try:
                _LW_CHARTS_JS = lw_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("lightweight-charts script okunamadı: %s", e)


def _fmt_money(val: float | Decimal | None) -> str:
    if val is None:
        return "0,00 ₺"
    try:
        return f"{float(val):,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"{val} ₺"


class PlanningController(QObject):
    """QML context property: planningController"""

    # --- Signals ---
    budgetChanged = Signal()
    goalsChanged = Signal()
    feasibilityChanged = Signal()
    dcaChanged = Signal()
    dcaRunningChanged = Signal()
    operationResult = Signal(bool, str, arguments=["success", "message"])

    def __init__(self, container, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._service = getattr(container, "planning_service", None)
        self._dca_service = getattr(container, "dca_backtest_service", None)

        # ── Bütçe Durumu ──
        now = datetime.now()
        self._current_month = f"{now.year}-{now.month:02d}"
        self._total_income: float = 0.0
        self._total_expense: float = 0.0
        self._net_savings_potential: float = 0.0
        self._savings_target: float = 0.0
        self._budget_status_msg: str = ""
        self._income_items: List[Dict[str, Any]] = []
        self._expense_items: List[Dict[str, Any]] = []
        self._available_months: List[str] = []

        # ── Hedefler Durumu ──
        self._goals_list: List[Dict[str, Any]] = []
        self._feasibility_status: str = "BİLGİ"
        self._feasibility_msg: str = ""
        self._total_monthly_need: float = 0.0
        self._monthly_power: float = 0.0

        # ── DCA Durumu ──
        self._dca_is_running: bool = False
        self._dca_total_invested: str = "0,00 ₺"
        self._dca_final_value: str = "0,00 ₺"
        self._dca_return_pct: float = 0.0
        self._dca_return_formatted: str = "%0.00"
        self._dca_contribution_count: int = 0
        self._dca_shares_list: List[Dict[str, Any]] = []
        self._dca_chart_html: str = ""

        # İlk veri yükleme
        self._refresh_available_months()
        self.loadBudgetForMonth(self._current_month)
        self.loadGoals()

    # ──────────────────────────── Bütçe QML Properties ────────────────────────────

    @Property(str, notify=budgetChanged)
    def currentMonth(self) -> str:
        return self._current_month

    @Property(list, notify=budgetChanged)
    def availableMonths(self) -> list:
        return self._available_months

    @Property(str, notify=budgetChanged)
    def totalIncomeFormatted(self) -> str:
        return _fmt_money(self._total_income)

    @Property(str, notify=budgetChanged)
    def totalExpenseFormatted(self) -> str:
        return _fmt_money(self._total_expense)

    @Property(str, notify=budgetChanged)
    def netSavingsPotentialFormatted(self) -> str:
        return _fmt_money(self._net_savings_potential)

    @Property(float, notify=budgetChanged)
    def netSavingsPotential(self) -> float:
        return self._net_savings_potential

    @Property(float, notify=budgetChanged)
    def savingsTarget(self) -> float:
        return self._savings_target

    @Property(str, notify=budgetChanged)
    def budgetStatusMessage(self) -> str:
        return self._budget_status_msg

    @Property(list, notify=budgetChanged)
    def incomeItems(self) -> list:
        return self._income_items

    @Property(list, notify=budgetChanged)
    def expenseItems(self) -> list:
        return self._expense_items

    # ──────────────────────────── Hedefler QML Properties ────────────────────────────

    @Property(list, notify=goalsChanged)
    def goalsList(self) -> list:
        return self._goals_list

    @Property(str, notify=feasibilityChanged)
    def feasibilityStatus(self) -> str:
        return self._feasibility_status

    @Property(str, notify=feasibilityChanged)
    def feasibilityMessage(self) -> str:
        return self._feasibility_msg

    @Property(str, notify=feasibilityChanged)
    def totalMonthlyNeedFormatted(self) -> str:
        return _fmt_money(self._total_monthly_need)

    @Property(str, notify=feasibilityChanged)
    def monthlyPowerFormatted(self) -> str:
        return _fmt_money(self._monthly_power)

    # ──────────────────────────── DCA QML Properties ────────────────────────────

    @Property(bool, notify=dcaRunningChanged)
    def dcaIsRunning(self) -> bool:
        return self._dca_is_running

    @Property(str, notify=dcaChanged)
    def dcaTotalInvested(self) -> str:
        return self._dca_total_invested

    @Property(str, notify=dcaChanged)
    def dcaFinalValue(self) -> str:
        return self._dca_final_value

    @Property(float, notify=dcaChanged)
    def dcaReturnPct(self) -> float:
        return self._dca_return_pct

    @Property(str, notify=dcaChanged)
    def dcaReturnFormatted(self) -> str:
        return self._dca_return_formatted

    @Property(int, notify=dcaChanged)
    def dcaContributionCount(self) -> int:
        return self._dca_contribution_count

    @Property(list, notify=dcaChanged)
    def dcaSharesList(self) -> list:
        return self._dca_shares_list

    @Property(str, notify=dcaChanged)
    def dcaChartHtml(self) -> str:
        return self._dca_chart_html

    def _refresh_available_months(self) -> None:
        """İlk veri tarihinden günümüze kadar bütçe aylarını üretir."""
        now = datetime.now()
        cur_year, cur_month = now.year, now.month

        start_year = cur_year - 1
        start_month = 1

        try:
            if self._service:
                budgets = self._service.get_all_budgets()
                if budgets:
                    oldest_b = min(b.month for b in budgets if b.month)
                    parts = oldest_b.split("-")
                    start_year = min(start_year, int(parts[0]))
                    start_month = min(start_month, int(parts[1]))

            conn_prov = getattr(self._container, "conn_provider", None)
            if conn_prov:
                with conn_prov.Session() as session:
                    from sqlalchemy import text
                    min_trade = session.execute(text("SELECT min(trade_date) FROM trades")).scalar()
                    if min_trade:
                        t_parts = str(min_trade)[:7].split("-")
                        start_year = min(start_year, int(t_parts[0]))
                        start_month = min(start_month, int(t_parts[1]))
        except Exception as exc:
            logger.warning("Bütçe ayları listelenirken hata: %s", exc)

        months = []
        y, m = start_year, start_month
        while (y < cur_year) or (y == cur_year and m <= cur_month):
            months.append(f"{y}-{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1

        months.reverse()  # En yeni ay en üstte olsun
        if self._current_month not in months:
            months.insert(0, self._current_month)
        self._available_months = months

    # ──────────────────────────── Bütçe Slotları ────────────────────────────

    @Slot(str)
    def loadBudgetForMonth(self, month: str) -> None:
        """Belirtilen ay için bütçeyi yükler."""
        if not self._service or not month:
            return
        self._current_month = month
        try:
            # Sabitlenmiş kalemler seti
            pinned_items = self._service.get_pinned_budget_items()
            pinned_set = {(p.item_type.upper(), p.name.strip().lower()) for p in pinned_items}

            budget = self._service.get_budget_for_month(month)
            if budget is None:
                # Taslak bütçe (sabitlenmiş kalemlerden oluşturulur)
                budget = self._service.get_budget_draft_from_pinned_items(month)

            self._total_income = float(budget.total_income)
            self._total_expense = float(budget.total_expense)
            self._net_savings_potential = float(budget.net_savings_potential)
            self._savings_target = float(budget.savings_target)
            self._budget_status_msg = budget.status_message or ""

            inc = []
            exp = []
            for item in budget.items:
                is_pinned = (item.item_type.upper(), item.name.strip().lower()) in pinned_set
                entry = {
                    "id": item.id or -1,
                    "name": item.name,
                    "amount": float(item.amount),
                    "amountFormatted": _fmt_money(item.amount),
                    "type": item.item_type,
                    "isPinned": is_pinned,
                }
                if item.item_type.upper() == "INCOME":
                    inc.append(entry)
                else:
                    exp.append(entry)

            self._income_items = inc
            self._expense_items = exp
            self.budgetChanged.emit()
        except Exception as exc:
            logger.exception("Bütçe yüklenemedi: %s", exc)

    @Slot(str, str, float, bool)
    def togglePinItem(self, item_type: str, name: str, amount: float, pin: bool) -> None:
        """Gelir veya gider kalemini pinler veya pinini kaldırır."""
        if not self._service or not name.strip():
            return
        try:
            if pin:
                self._service.pin_budget_item(item_type.upper(), name.strip(), amount)
                self.operationResult.emit(True, f"'{name}' kalemi sabitlendi (gelecek aylara otomatik aktarılacak).")
            else:
                self._service.unpin_budget_item(item_type.upper(), name.strip())
                self.operationResult.emit(True, f"'{name}' kaleminin sabitlemesi kaldırıldı.")

            items = self._income_items if item_type.upper() == "INCOME" else self._expense_items
            clean_name = name.strip().lower()
            for it in items:
                if it["name"].strip().lower() == clean_name:
                    it["isPinned"] = pin
            self.budgetChanged.emit()
        except Exception as exc:
            logger.exception("Pinleme işlemi başarısız: %s", exc)
            self.operationResult.emit(False, str(exc))

    @Slot(str, str, float)
    def addBudgetItem(self, item_type: str, name: str, amount: float) -> None:
        """Geçici listeye bütçe kalemi ekler ve toplamları günceller."""
        if not name.strip() or amount <= 0:
            return

        # Pinned kontrolü
        is_pinned = False
        try:
            pinned_items = self._service.get_pinned_budget_items()
            pinned_set = {(p.item_type.upper(), p.name.strip().lower()) for p in pinned_items}
            is_pinned = (item_type.upper(), name.strip().lower()) in pinned_set
        except Exception:
            pass

        entry = {
            "id": -1,
            "name": name.strip(),
            "amount": float(amount),
            "amountFormatted": _fmt_money(amount),
            "type": item_type.upper(),
            "isPinned": is_pinned,
        }

        if item_type.upper() == "INCOME":
            self._income_items.append(entry)
        else:
            self._expense_items.append(entry)

        self._recalculate_budget_totals()
        self.budgetChanged.emit()

    @Slot(str, int)
    def removeBudgetItem(self, item_type: str, index: int) -> None:
        """Listeden kalemi çıkarır."""
        if item_type.upper() == "INCOME" and 0 <= index < len(self._income_items):
            self._income_items.pop(index)
        elif item_type.upper() != "INCOME" and 0 <= index < len(self._expense_items):
            self._expense_items.pop(index)

        self._recalculate_budget_totals()
        self.budgetChanged.emit()

    @Slot(str, int, str, float)
    def updateBudgetItem(self, item_type: str, index: int, new_name: str, new_amount: float) -> None:
        """Bütçe kalemini düzenler, pinli ise şablonunu senkronize eder ve toplamları günceller."""
        if not new_name.strip() or new_amount <= 0:
            self.operationResult.emit(False, "Kalem adı boş olamaz ve tutar 0'dan büyük olmalıdır.")
            return

        is_income = item_type.upper() == "INCOME"
        items_list = self._income_items if is_income else self._expense_items

        if not (0 <= index < len(items_list)):
            self.operationResult.emit(False, "Geçersiz kalem seçimi.")
            return

        target_item = items_list[index]
        old_name = target_item["name"]
        old_pinned = target_item.get("isPinned", False)

        target_item["name"] = new_name.strip()
        target_item["amount"] = float(new_amount)
        target_item["amountFormatted"] = _fmt_money(new_amount)

        # Eğer sabitlenmiş (pinned) bir kalemse ve adı/tutarı değiştiyse şablonu da güncelle
        if old_pinned and self._service:
            try:
                if old_name.strip().lower() != new_name.strip().lower():
                    self._service.unpin_budget_item(item_type.upper(), old_name.strip())
                self._service.pin_budget_item(item_type.upper(), new_name.strip(), float(new_amount))
            except Exception as exc:
                logger.warning("Pin şablonu güncellenirken hata: %s", exc)

        self._recalculate_budget_totals()
        self.budgetChanged.emit()
        self.operationResult.emit(True, f"'{new_name.strip()}' kalemi güncellendi.")

    @Slot(float)
    def saveCurrentBudget(self, savings_target: float) -> None:
        """Mevcut kalemleri ve tasarruf hedefini veritabanına kaydeder."""
        if not self._service:
            return
        try:
            items: List[BudgetItem] = []
            for entry in self._income_items:
                items.append(BudgetItem(
                    id=None if entry["id"] == -1 else entry["id"],
                    budget_id=None,
                    item_type="INCOME",
                    name=entry["name"],
                    amount=Decimal(str(entry["amount"])),
                ))
            for entry in self._expense_items:
                items.append(BudgetItem(
                    id=None if entry["id"] == -1 else entry["id"],
                    budget_id=None,
                    item_type="EXPENSE",
                    name=entry["name"],
                    amount=Decimal(str(entry["amount"])),
                ))

            budget = Budget(
                id=None,
                month=self._current_month,
                savings_target=Decimal(str(savings_target)),
                items=items,
            )
            saved = self._service.save_budget(budget)
            self._savings_target = float(saved.savings_target)
            self._recalculate_budget_totals()
            self.budgetChanged.emit()
            self.loadGoals()  # Bütçe değişince hedef fizibilitesi güncellensin
            self.operationResult.emit(True, f"{self._current_month} bütçesi başarıyla kaydedildi.")
        except Exception as exc:
            logger.exception("Bütçe kaydedilemedi: %s", exc)
            self.operationResult.emit(False, str(exc))

    def _recalculate_budget_totals(self) -> None:
        self._total_income = sum(item["amount"] for item in self._income_items)
        self._total_expense = sum(item["amount"] for item in self._expense_items)
        self._net_savings_potential = self._total_income - self._total_expense
        if self._savings_target > 0:
            if self._net_savings_potential >= self._savings_target:
                self._budget_status_msg = f"Hedef tutturuldu! (+{_fmt_money(self._net_savings_potential - self._savings_target)} fazlalık)"
            else:
                self._budget_status_msg = f"Hedefin altındasınız ({_fmt_money(self._savings_target - self._net_savings_potential)} eksik)"
        else:
            self._budget_status_msg = f"Net tasarruf gücü: {_fmt_money(self._net_savings_potential)}"

    # ──────────────────────────── Hedefler Slotları ────────────────────────────

    @Slot()
    def loadGoals(self) -> None:
        """Kayıtlı tüm hedefleri ve fizibilite analizini yükler."""
        if not self._service:
            return
        try:
            goals = self._service.get_all_goals()
            goals_list = []
            for g in goals:
                progress = min(1.0, float(g.progress_ratio))
                prio_val = str(g.priority).upper()
                prio_tr = "YÜKSEK" if prio_val == "HIGH" else ("DÜŞÜK" if prio_val == "LOW" else "ORTA")
                goals_list.append({
                    "id": g.id,
                    "name": g.name,
                    "targetAmount": float(g.target_amount),
                    "targetAmountFormatted": _fmt_money(g.target_amount),
                    "currentAmount": float(g.current_amount),
                    "currentAmountFormatted": _fmt_money(g.current_amount),
                    "remainingAmount": float(g.remaining_amount),
                    "remainingAmountFormatted": _fmt_money(g.remaining_amount),
                    "deadline": g.deadline.isoformat() if hasattr(g.deadline, "isoformat") else str(g.deadline),
                    "priority": prio_val,
                    "priorityTr": prio_tr,
                    "status": g.status.value if hasattr(g.status, "value") else str(g.status),
                    "isCompleted": g.is_completed,
                    "progress": progress,
                    "progressPct": f"%{progress * 100:.1f}",
                    "monthsRemaining": g.months_remaining(),
                    "requiredMonthlyFormatted": _fmt_money(g.required_monthly_contribution()),
                })
            self._goals_list = goals_list
            self.goalsChanged.emit()

            # Fizibilite
            feasibility = self._service.analyze_feasibility()
            self._feasibility_status = feasibility.get("status", "BİLGİ")
            self._feasibility_msg = feasibility.get("message", "")
            self._total_monthly_need = float(feasibility.get("total_monthly_need", 0.0))
            self._monthly_power = float(feasibility.get("monthly_power", 0.0))
            self.feasibilityChanged.emit()
        except Exception as exc:
            logger.exception("Hedefler yüklenemedi: %s", exc)

    @Slot(str, float, str, str)
    def addGoal(self, name: str, target: float, deadline_str: str, priority: str = "MEDIUM") -> None:
        """Yeni hedef ekler."""
        if not self._service:
            return
        try:
            d_parts = [int(p) for p in deadline_str.split("-")]
            deadline = date(d_parts[0], d_parts[1], d_parts[2])
            p_map = {"DÜŞÜK": "LOW", "ORTA": "MEDIUM", "YÜKSEK": "HIGH", "LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}
            prio_clean = p_map.get(str(priority).strip().upper(), "MEDIUM")
            self._service.add_goal(name, target, deadline, prio_clean)
            self.loadGoals()
            self.operationResult.emit(True, f"'{name}' hedefi eklendi.")
        except Exception as exc:
            logger.exception("Hedef eklenemedi: %s", exc)
            self.operationResult.emit(False, str(exc))

    @Slot(int, str, float, str, str)
    def updateGoal(self, goal_id: int, name: str, target: float, deadline_str: str, priority: str = "MEDIUM") -> None:
        """Mevcut finansal hedefi günceller."""
        if not self._service:
            return
        try:
            d_parts = [int(p) for p in deadline_str.split("-")]
            deadline = date(d_parts[0], d_parts[1], d_parts[2])
            p_map = {"DÜŞÜK": "LOW", "ORTA": "MEDIUM", "YÜKSEK": "HIGH", "LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}
            prio_clean = p_map.get(str(priority).strip().upper(), "MEDIUM")
            self._service.update_goal(goal_id, name, target, deadline, prio_clean)
            self.loadGoals()
            self.operationResult.emit(True, f"'{name}' hedefi güncellendi.")
        except Exception as exc:
            logger.exception("Hedef güncellenemedi: %s", exc)
            self.operationResult.emit(False, str(exc))

    @Slot(int)
    def deleteGoal(self, goal_id: int) -> None:
        """Hedefi siler."""
        if not self._service:
            return
        try:
            self._service.delete_goal(goal_id)
            self.loadGoals()
            self.operationResult.emit(True, "Hedef silindi.")
        except Exception as exc:
            logger.exception("Hedef silinemedi: %s", exc)
            self.operationResult.emit(False, str(exc))

    @Slot(int, float)
    def addContribution(self, goal_id: int, amount: float) -> None:
        """Hedefe katkı ekler."""
        if not self._service:
            return
        try:
            self._service.add_contribution(goal_id, amount)
            self.loadGoals()
            self.operationResult.emit(True, f"Hedefe {_fmt_money(amount)} eklendi.")
        except Exception as exc:
            logger.exception("Katkı eklenemedi: %s", exc)
            self.operationResult.emit(False, str(exc))

    # ──────────────────────────── DCA Backtest Slotları ────────────────────────────

    @Slot(str, float, str, str)
    def runDcaBacktest(self, tickers_str: str, amount: float, start_date_str: str, end_date_str: str) -> None:
        """DCA simülasyonunu çalıştırır."""
        if not self._dca_service:
            self.operationResult.emit(False, "DCA simülasyon servisi bulunamadı.")
            return

        self._dca_is_running = True
        self.dcaRunningChanged.emit()

        tickers = [t.strip().upper() for t in tickers_str.replace(",", " ").split() if t.strip()]
        if not tickers:
            self._dca_is_running = False
            self.dcaRunningChanged.emit()
            self.operationResult.emit(False, "En az bir hisse kodu girin.")
            return

        try:
            s_parts = [int(p) for p in start_date_str.split("-")]
            e_parts = [int(p) for p in end_date_str.split("-")]
            s_date = date(s_parts[0], s_parts[1], s_parts[2])
            e_date = date(e_parts[0], e_parts[1], e_parts[2])
        except Exception:
            s_date = date(2023, 1, 1)
            e_date = date.today()

        # Timer ile UI dondurmadan hesapla
        QTimer.singleShot(50, lambda: self._execute_dca(tickers, Decimal(str(amount)), s_date, e_date))

    def _execute_dca(self, tickers: List[str], amount: Decimal, s_date: date, e_date: date) -> None:
        try:
            # Fiyatlar DuckDB piyasa geçmişinden okunur (tüm BIST); `stocks` tablosuna hisse eklenmez
            resolved_tickers = [t.strip().upper().replace(".IS", "") for t in tickers if t and t.strip()]

            res = self._dca_service.run(
                tickers=resolved_tickers,
                monthly_contribution=amount,
                start_date=s_date,
                end_date=e_date,
            )

            self._dca_total_invested = _fmt_money(res.total_invested)
            self._dca_final_value = _fmt_money(res.final_value)
            self._dca_return_pct = float(res.total_return_pct) if res.total_return_pct is not None else 0.0
            self._dca_return_formatted = f"%{self._dca_return_pct:+.2f}"
            self._dca_contribution_count = res.contribution_count

            # Hisse lot adetleri
            shares = []
            for t, q in res.shares_by_ticker.items():
                shares.append({
                    "ticker": t,
                    "quantity": float(q),
                    "quantityFormatted": f"{float(q):,.2f} Lot",
                })
            self._dca_shares_list = shares

            # Chart HTML
            self._dca_chart_html = self._build_dca_chart_html(res.portfolio_value_series)

            self.dcaChanged.emit()
            self.operationResult.emit(True, f"DCA simülasyonu tamamlandı ({res.contribution_count} katkı dönemi).")
        except Exception as exc:
            logger.exception("DCA simülasyon hatası: %s", exc)
            self.operationResult.emit(False, str(exc))
        finally:
            self._dca_is_running = False
            self.dcaRunningChanged.emit()

    def _build_dca_chart_html(self, series: Dict[date, Decimal]) -> str:
        if not series:
            return ""
        _load_embedded_scripts()
        script_tag = f"<script>{_LW_CHARTS_JS}</script>" if _LW_CHARTS_JS else '<script src="https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js"></script>'

        data_points = []
        for dt_val in sorted(series.keys()):
            val = float(series[dt_val])
            data_points.append(f"{{time:'{dt_val.isoformat()}',value:{val:.2f}}}")

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin: 0; background: #131722; overflow: hidden; }}
#c {{ width: 100vw; height: 100vh; }}
</style>
{script_tag}
</head><body><div id="c"></div>
<script>
var chart = LightweightCharts.createChart(document.getElementById('c'), {{
    width: window.innerWidth || 800, height: window.innerHeight || 450,
    layout: {{ background: {{ color: '#131722' }}, textColor: '#9db2ce' }},
    grid: {{ vertLines: {{ color: '#1e222d' }}, horzLines: {{ color: '#1e222d' }} }},
    rightPriceScale: {{ borderColor: '#2a2e39', scaleMargins: {{ top: 0.1, bottom: 0.1 }} }},
    timeScale: {{ borderColor: '#2a2e39', timeVisible: false }},
    crosshair: {{ mode: 0 }}
}});
var areaSeries = chart.addSeries(LightweightCharts.AreaSeries, {{
    topColor: 'rgba(41, 98, 255, 0.45)',
    bottomColor: 'rgba(41, 98, 255, 0.04)',
    lineColor: '#2962ff',
    lineWidth: 2,
    priceFormat: {{
        type: 'price',
        precision: 2,
        minMove: 0.01,
    }},
    title: 'Portföy Değeri (₺)',
}});
areaSeries.setData([{','.join(data_points)}]);
chart.timeScale().fitContent();
window.addEventListener('resize', function() {{
    chart.applyOptions({{ width: window.innerWidth, height: window.innerHeight }});
}});
</script></body></html>"""
