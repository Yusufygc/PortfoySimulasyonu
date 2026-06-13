from src.qt_compat.scaling import (
    configure_qt_scale_normalization,
    qt_scale_factor_for_percent,
)


def test_qt_scale_factor_for_percent_counter_scales_common_windows_scale():
    assert qt_scale_factor_for_percent(100) is None
    assert qt_scale_factor_for_percent(125) == "0.8"
    assert qt_scale_factor_for_percent(150) == "0.667"


def test_configure_qt_scale_normalization_sets_env_when_needed():
    env = {}

    factor = configure_qt_scale_normalization(
        env=env,
        scale_percent_provider=lambda: 125,
    )

    assert factor == "0.8"
    assert env["QT_SCALE_FACTOR"] == "0.8"
    assert env["QT_SCALE_FACTOR_ROUNDING_POLICY"] == "PassThrough"


def test_configure_qt_scale_normalization_respects_existing_env():
    env = {"QT_SCALE_FACTOR": "1.25"}

    factor = configure_qt_scale_normalization(
        env=env,
        scale_percent_provider=lambda: 125,
    )

    assert factor is None
    assert env["QT_SCALE_FACTOR"] == "1.25"
