import pytest

pytest.importorskip("pyqtgraph")

from movak.gui.timeline.navigation_viewbox import _event_delta


class DeltaEvent:
    def delta(self) -> int:
        return 120


class AngleDeltaPoint:
    def __init__(self, y_value: int) -> None:
        self._y_value = y_value

    def y(self) -> int:
        return self._y_value


class AngleDeltaEvent:
    def angleDelta(self) -> AngleDeltaPoint:
        return AngleDeltaPoint(-90)


def test_event_delta_prefers_delta_method():
    assert _event_delta(DeltaEvent()) == 120


def test_event_delta_falls_back_to_angle_delta():
    assert _event_delta(AngleDeltaEvent()) == -90
