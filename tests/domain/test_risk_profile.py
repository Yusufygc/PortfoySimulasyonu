import pytest

from src.domain.models.risk_profile import (
    Horizon,
    PROFILE_INFO,
    Reaction,
    RiskLabel,
    RiskProfile,
)


def test_risk_profile_defaults_recommended_allocation_from_label():
    profile = RiskProfile(
        id=None,
        age=35,
        horizon=Horizon.MEDIUM,
        reaction=Reaction.HOLD,
        risk_label=RiskLabel.BUYUME_ODAKLI,
    )

    assert profile.recommended_allocation == PROFILE_INFO[RiskLabel.BUYUME_ODAKLI]["allocation"]
    assert profile.description == PROFILE_INFO[RiskLabel.BUYUME_ODAKLI]["description"]
    assert profile.max_volatility == PROFILE_INFO[RiskLabel.BUYUME_ODAKLI]["max_volatility"]


def test_risk_profile_display_values_are_mapped():
    profile = RiskProfile(
        id=None,
        age=35,
        horizon=Horizon.LONG,
        reaction=Reaction.BUY_MORE,
    )

    assert "Uzun Vade" in profile.horizon_display
    assert "Daha Çok" in profile.reaction_display


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("age", -1, "Age"),
        ("horizon", "invalid", "horizon"),
        ("reaction", "invalid", "reaction"),
        ("risk_score", -1, "Risk score"),
        ("risk_label", "invalid", "risk label"),
    ],
)
def test_risk_profile_rejects_invalid_values(field, value, message):
    kwargs = {
        "id": None,
        "age": 35,
        "horizon": Horizon.MEDIUM,
        "reaction": Reaction.HOLD,
        "risk_score": 0,
        "risk_label": RiskLabel.DENGELI,
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        RiskProfile(**kwargs)
