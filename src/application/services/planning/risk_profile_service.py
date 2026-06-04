# src/application/services/planning/risk_profile_service.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence

from src.domain.models.risk_profile import (
    PROFILE_INFO,
    Horizon,
    Reaction,
    RiskLabel,
    RiskProfile,
)
from src.domain.ports.repositories.i_risk_profile_repo import IRiskProfileRepository


QUESTIONNAIRE_VERSION = "professional_v1"


@dataclass(frozen=True)
class RiskOption:
    value: str
    label: str
    score: int


@dataclass(frozen=True)
class RiskQuestion:
    id: str
    title: str
    dimension: str
    options: Sequence[RiskOption]


@dataclass(frozen=True)
class RiskQuestionSection:
    title: str
    questions: Sequence[RiskQuestion]


DIMENSION_LABELS = {
    "capacity": "Risk Kapasitesi",
    "tolerance": "Risk Toleransı",
    "knowledge": "Bilgi ve Tecrübe",
    "goals": "Hedef ve Likidite",
}

DIMENSION_WEIGHTS = {
    "capacity": 0.30,
    "tolerance": 0.30,
    "knowledge": 0.20,
    "goals": 0.20,
}


def _opts(*items: tuple[str, str, int]) -> tuple[RiskOption, ...]:
    return tuple(RiskOption(value=value, label=label, score=score) for value, label, score in items)


QUESTIONNAIRE_SECTIONS: tuple[RiskQuestionSection, ...] = (
    RiskQuestionSection(
        "Finansal Durum",
        (
            RiskQuestion(
                "age",
                "Yaş aralığınız nedir?",
                "capacity",
                _opts(
                    ("60_plus", "60 ve üzeri", 1),
                    ("50_59", "50-59", 2),
                    ("35_49", "35-49", 3),
                    ("25_34", "25-34", 4),
                    ("18_24", "18-24", 5),
                ),
            ),
            RiskQuestion(
                "income_stability",
                "Geliriniz ne kadar istikrarlı?",
                "capacity",
                _opts(
                    ("unstable", "Düzenli gelirim yok", 0),
                    ("variable", "Gelirim belirgin dalgalanıyor", 2),
                    ("mostly_stable", "Genelde düzenli", 4),
                    ("stable", "Çok düzenli ve öngörülebilir", 5),
                ),
            ),
            RiskQuestion(
                "emergency_fund",
                "Acil durum fonunuz kaç aylık giderinizi karşılar?",
                "capacity",
                _opts(
                    ("none", "Yok", 0),
                    ("lt_1", "1 aydan az", 1),
                    ("1_3", "1-3 ay", 3),
                    ("3_6", "3-6 ay", 4),
                    ("6_plus", "6 ay ve üzeri", 5),
                ),
            ),
            RiskQuestion(
                "debt_load",
                "Aylık borç/gelir yükünüz hangi seviyede?",
                "capacity",
                _opts(
                    ("high", "%50 üzeri", 0),
                    ("medium_high", "%30-50", 2),
                    ("medium", "%10-30", 4),
                    ("low", "%10 altı veya yok", 5),
                ),
            ),
        ),
    ),
    RiskQuestionSection(
        "Yatırım Hedefi",
        (
            RiskQuestion(
                "horizon",
                "Bu yatırımları genel olarak ne kadar süre tutmayı planlıyorsunuz?",
                "goals",
                _opts(
                    ("short", "0-12 ay", 1),
                    ("medium", "1-3 yıl", 3),
                    ("long", "3-7 yıl", 4),
                    ("very_long", "7 yıl ve üzeri", 5),
                ),
            ),
            RiskQuestion(
                "liquidity_need",
                "Yatırdığınız paraya yakın zamanda ihtiyacınız olabilir mi?",
                "goals",
                _opts(
                    ("very_high", "Evet, her an ihtiyaç olabilir", 0),
                    ("high", "1 yıl içinde ihtiyaç olabilir", 2),
                    ("medium", "Bir kısmına ihtiyaç olabilir", 3),
                    ("low", "Büyük olasılıkla ihtiyaç olmaz", 5),
                ),
            ),
            RiskQuestion(
                "investment_goal",
                "Ana yatırım hedefiniz hangisine daha yakın?",
                "goals",
                _opts(
                    ("capital_preservation", "Sermayeyi korumak", 1),
                    ("income", "Düzenli gelir elde etmek", 2),
                    ("balanced_growth", "Dengeli büyüme", 3),
                    ("growth", "Uzun vadeli büyüme", 4),
                    ("high_growth", "Yüksek büyüme potansiyeli", 5),
                ),
            ),
            RiskQuestion(
                "monthly_contribution",
                "Portföye düzenli katkıda bulunma imkanınız nedir?",
                "capacity",
                _opts(
                    ("none", "Katkı yapamam", 1),
                    ("occasional", "Ara sıra yapabilirim", 2),
                    ("regular_small", "Düzenli küçük katkılar", 4),
                    ("regular_high", "Düzenli ve güçlü katkılar", 5),
                ),
            ),
        ),
    ),
    RiskQuestionSection(
        "Risk Toleransı",
        (
            RiskQuestion(
                "loss_10",
                "Portföyünüz kısa sürede %10 düşerse ne yaparsınız?",
                "tolerance",
                _opts(
                    ("sell", "Satar ve riski azaltırım", 0),
                    ("reduce", "Bir kısmını azaltırım", 2),
                    ("hold", "Beklerim", 4),
                    ("buy_more", "Ek alım yaparım", 5),
                ),
            ),
            RiskQuestion(
                "loss_20",
                "Portföyünüz bir ayda %20 düşerse tepkiniz ne olur?",
                "tolerance",
                _opts(
                    ("sell", "Hemen satarım", 0),
                    ("reduce", "Pozisyon azaltırım", 1),
                    ("hold", "Planıma sadık kalırım", 4),
                    ("buy_more", "Fırsat olarak görürüm", 5),
                ),
            ),
            RiskQuestion(
                "loss_35",
                "Çok stresli piyasada %35 düşüş yaşanırsa hangi seçenek size daha yakın?",
                "tolerance",
                _opts(
                    ("exit", "Piyasadan çıkarım", 0),
                    ("protect", "Riski sert şekilde azaltırım", 1),
                    ("rebalance", "Dengeleme yaparım", 3),
                    ("stay", "Uzun vadeli plana devam ederim", 4),
                    ("increase", "Kademeli alımları artırırım", 5),
                ),
            ),
        ),
    ),
    RiskQuestionSection(
        "Bilgi ve Tecrübe",
        (
            RiskQuestion(
                "stock_experience",
                "Hisse senedi deneyiminiz nedir?",
                "knowledge",
                _opts(
                    ("none", "Yok", 0),
                    ("basic", "Temel seviyede", 2),
                    ("moderate", "Birkaç yıldır işlem yapıyorum", 4),
                    ("advanced", "İleri seviyede takip ediyorum", 5),
                ),
            ),
            RiskQuestion(
                "fund_bond_fx_experience",
                "Fon, tahvil/bono, döviz veya altın ürünlerinde deneyiminiz nedir?",
                "knowledge",
                _opts(
                    ("none", "Yok", 0),
                    ("basic", "Az", 2),
                    ("moderate", "Orta", 4),
                    ("advanced", "Yüksek", 5),
                ),
            ),
            RiskQuestion(
                "derivative_experience",
                "Kaldıraçlı/türev ürünleri ne kadar tanıyorsunuz?",
                "knowledge",
                _opts(
                    ("none", "Tanımıyorum", 0),
                    ("aware", "Sadece genel bilgim var", 1),
                    ("limited", "Sınırlı deneyimim var", 3),
                    ("experienced", "Risklerini bilerek kullandım", 5),
                ),
            ),
            RiskQuestion(
                "concentration_preference",
                "Portföy yoğunlaşması konusunda tercihiniz nedir?",
                "tolerance",
                _opts(
                    ("very_diversified", "Çok çeşitlendirilmiş portföy", 1),
                    ("diversified", "Dengeli çeşitlendirme", 3),
                    ("focused", "Sınırlı sayıda güçlü fikir", 4),
                    ("concentrated", "Yüksek yoğunlaşma kabul ederim", 5),
                ),
            ),
        ),
    ),
)


class RiskProfileService:
    """Risk profili anketini skorlar, gerekcelendirir ve kaydeder."""

    def __init__(self, risk_profile_repo: IRiskProfileRepository) -> None:
        self._repo = risk_profile_repo

    def get_current_profile(self) -> Optional[RiskProfile]:
        return self._repo.get_latest_profile()

    def get_questionnaire(self) -> tuple[RiskQuestionSection, ...]:
        return QUESTIONNAIRE_SECTIONS

    def calculate_and_save_profile(
        self,
        answers: Optional[Mapping[str, str]] = None,
        age: Optional[int] = None,
        horizon: Optional[str] = None,
        reaction: Optional[str] = None,
    ) -> RiskProfile:
        if isinstance(answers, int):
            return self._calculate_legacy_and_save(int(answers), str(age), str(horizon))
        if answers is None:
            if age is None or horizon is None or reaction is None:
                raise ValueError("Risk profili hesaplamak icin anket yanitlari gereklidir.")
            return self._calculate_legacy_and_save(age, horizon, reaction)

        clean_answers = self._validate_answers(answers)
        dimension_scores = self._calculate_dimension_scores(clean_answers)
        raw_score = self._calculate_weighted_score(dimension_scores)
        adjusted_score, notes = self._apply_consistency_checks(raw_score, dimension_scores, clean_answers)
        label = self._score_to_label(adjusted_score)
        allocation = dict(PROFILE_INFO[label]["allocation"])

        profile = RiskProfile(
            id=None,
            age=self._age_from_answer(clean_answers["age"]),
            horizon=self._horizon_from_answer(clean_answers["horizon"]),
            reaction=self._reaction_from_answers(clean_answers),
            risk_score=adjusted_score,
            risk_label=label,
            questionnaire_version=QUESTIONNAIRE_VERSION,
            answers=clean_answers,
            dimension_scores=dimension_scores,
            recommended_allocation=allocation,
            suitability_notes=notes,
        )
        return self._repo.save_profile(profile)

    def _calculate_legacy_and_save(self, age: int, horizon: str, reaction: str) -> RiskProfile:
        if age <= 0:
            raise ValueError("Yas pozitif olmalidir.")

        score = self._calculate_legacy_score(age, horizon, reaction)
        label = self._score_to_label(score)
        profile = RiskProfile(
            id=None,
            age=age,
            horizon=horizon,
            reaction=reaction,
            risk_score=score,
            risk_label=label,
            questionnaire_version="legacy",
            recommended_allocation=dict(PROFILE_INFO[label]["allocation"]),
        )
        return self._repo.save_profile(profile)

    @staticmethod
    def _calculate_legacy_score(age: int, horizon: str, reaction: str) -> int:
        score = 0
        if age < 30:
            score += 30
        elif age < 50:
            score += 20
        else:
            score += 10

        if horizon == Horizon.LONG:
            score += 30
        elif horizon == Horizon.MEDIUM:
            score += 20
        else:
            score += 10

        if reaction == Reaction.BUY_MORE:
            score += 40
        elif reaction == Reaction.HOLD:
            score += 20

        return max(0, min(100, score))

    def _validate_answers(self, answers: Mapping[str, str]) -> Dict[str, str]:
        answer_map = {str(key): str(value) for key, value in answers.items()}
        valid_values = {
            question.id: {option.value for option in question.options}
            for question in self._all_questions()
        }

        missing = [question_id for question_id in valid_values if question_id not in answer_map]
        if missing:
            raise ValueError(f"Eksik anket yanıtları: {', '.join(missing)}")

        invalid = [
            question_id
            for question_id, value in answer_map.items()
            if question_id in valid_values and value not in valid_values[question_id]
        ]
        if invalid:
            raise ValueError(f"Geçersiz anket yanıtları: {', '.join(invalid)}")

        return {question_id: answer_map[question_id] for question_id in valid_values}

    def _calculate_dimension_scores(self, answers: Mapping[str, str]) -> Dict[str, int]:
        grouped: Dict[str, List[int]] = {dimension: [] for dimension in DIMENSION_WEIGHTS}
        for question in self._all_questions():
            selected = answers[question.id]
            option = next(option for option in question.options if option.value == selected)
            grouped[question.dimension].append(option.score)

        return {
            dimension: round((sum(scores) / (len(scores) * 5)) * 100) if scores else 0
            for dimension, scores in grouped.items()
        }

    @staticmethod
    def _calculate_weighted_score(dimension_scores: Mapping[str, int]) -> int:
        score = sum(dimension_scores[dimension] * weight for dimension, weight in DIMENSION_WEIGHTS.items())
        return round(score)

    def _apply_consistency_checks(
        self,
        score: int,
        dimension_scores: Mapping[str, int],
        answers: Mapping[str, str],
    ) -> tuple[int, List[str]]:
        notes: List[str] = [
            "Bu sonuç yatırım tavsiyesi değil, risk profiline uygun genel dağılım örneğidir."
        ]
        adjusted = score

        if dimension_scores["tolerance"] >= 75 and dimension_scores["capacity"] < 45:
            adjusted -= 10
            notes.append("Risk alma isteğiniz yüksek olsa da finansal kapasite skorunuz sınırlayıcı görünüyor.")

        if answers["horizon"] == "short" and dimension_scores["tolerance"] >= 70:
            adjusted -= 8
            notes.append("Kısa yatırım vadesi yüksek riskli varlık ağırlığını sınırlandırır.")

        if dimension_scores["knowledge"] < 35 and (score >= 65 or dimension_scores["tolerance"] >= 70):
            adjusted -= 10
            notes.append("Bilgi/tecrübe skoru düşük olduğu için riskin kademeli artırılması daha uygundur.")

        return max(0, min(100, round(adjusted))), notes

    @staticmethod
    def _score_to_label(score: int) -> str:
        if score <= 24:
            return RiskLabel.COK_MUHAFAZAKAR
        if score <= 44:
            return RiskLabel.MUHAFAZAKAR
        if score <= 64:
            return RiskLabel.DENGELI
        if score <= 79:
            return RiskLabel.BUYUME_ODAKLI
        return RiskLabel.AGRESIF

    @staticmethod
    def _age_from_answer(value: str) -> int:
        return {
            "18_24": 22,
            "25_34": 30,
            "35_49": 42,
            "50_59": 55,
            "60_plus": 65,
        }.get(value, 30)

    @staticmethod
    def _horizon_from_answer(value: str) -> str:
        if value == "short":
            return Horizon.SHORT
        if value in {"medium", "long"}:
            return Horizon.MEDIUM
        return Horizon.LONG

    @staticmethod
    def _reaction_from_answers(answers: Mapping[str, str]) -> str:
        loss_20 = answers.get("loss_20")
        if loss_20 in {"sell", "reduce"}:
            return Reaction.SELL
        if loss_20 == "buy_more":
            return Reaction.BUY_MORE
        return Reaction.HOLD

    @staticmethod
    def _all_questions() -> List[RiskQuestion]:
        return [question for section in QUESTIONNAIRE_SECTIONS for question in section.questions]
