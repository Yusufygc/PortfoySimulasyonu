from src.qt_compat.scaling import (
    configure_qt_scale_normalization,
    qt_scale_factor_for_percent,
)


def test_qt_scale_factor_for_percent_does_not_counter_scale_windows_dpi():
    assert qt_scale_factor_for_percent(100) is None
    assert qt_scale_factor_for_percent(125) is None
    assert qt_scale_factor_for_percent(150) is None
    assert qt_scale_factor_for_percent(200) is None


def test_configure_qt_scale_normalization_sets_passthrough_without_qt_scale_factor():
    env = {}

    result = configure_qt_scale_normalization(
        env=env,
        scale_percent_provider=lambda: 200,
    )

    assert result == "PassThrough"
    assert env.get("QT_SCALE_FACTOR") is None
    assert env["QT_SCALE_FACTOR_ROUNDING_POLICY"] == "PassThrough"


def test_configure_qt_scale_normalization_respects_existing_env_and_disable_flag():
    env_explicit = {"QT_SCALE_FACTOR": "1.25", "QT_SCALE_FACTOR_ROUNDING_POLICY": "Round"}
    result_explicit = configure_qt_scale_normalization(
        env=env_explicit,
        scale_percent_provider=lambda: 125,
    )
    assert result_explicit is None
    assert env_explicit["QT_SCALE_FACTOR"] == "1.25"
    assert env_explicit["QT_SCALE_FACTOR_ROUNDING_POLICY"] == "Round"

    env_disabled = {"PORTFOYSIM_DISABLE_QT_SCALE_NORMALIZATION": "1"}
    result_disabled = configure_qt_scale_normalization(
        env=env_disabled,
        scale_percent_provider=lambda: 200,
    )
    assert result_disabled is None
    assert "QT_SCALE_FACTOR" not in env_disabled
    assert "QT_SCALE_FACTOR_ROUNDING_POLICY" not in env_disabled
