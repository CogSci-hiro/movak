"""Interval tests."""

from movak.core.interval import Interval


def test_interval_duration_overlap_and_contains() -> None:
    """Intervals expose basic temporal helpers."""
    left = Interval(start=0.0, end=0.5, label="a")
    right = Interval(start=0.25, end=0.75, label="b")

    assert left.duration() == 0.5
    assert left.overlaps(right) is True
    assert left.contains(0.25) is True
    assert left.contains(0.75) is False
