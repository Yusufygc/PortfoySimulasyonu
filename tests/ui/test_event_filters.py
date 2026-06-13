import pytest

pytest.importorskip("PySide6")

from src.qt_compat.qtcore import QEvent
from src.qt_compat.qtwidgets import QComboBox, QWidget

from src.ui.shared.event_filters import GlobalWheelEventFilter


def test_global_wheel_event_filter_blocks_combo_wheel(qapp):
    combo = QComboBox()
    event_filter = GlobalWheelEventFilter()
    event = QEvent(QEvent.Wheel)

    assert event_filter.eventFilter(combo, event) is True
    assert event.isAccepted()


def test_global_wheel_event_filter_returns_false_for_unhandled_event(qapp):
    widget = QWidget()
    event_filter = GlobalWheelEventFilter()
    event = QEvent(QEvent.MouseButtonPress)

    assert event_filter.eventFilter(widget, event) is False


def test_global_wheel_event_filter_swallows_deleted_qobject_runtime_error(qapp):
    class BrokenEvent:
        def type(self):
            raise RuntimeError("Internal C++ object already deleted")

    event_filter = GlobalWheelEventFilter()

    assert event_filter.eventFilter(object(), BrokenEvent()) is False
