"""Split operation tests."""

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.operations.split import SplitIntervalOperation


def test_split_interval_operation_creates_two_intervals() -> None:
    """Split operations replace one interval with two."""
    interval = Interval(start=0.0, end=1.0, label="aa")
    recording = Recording(id="rec-1", tiers={"phones": Tier(name="phones", intervals=[interval])})
    operation = SplitIntervalOperation(
        tier_name="phones",
        token_id=interval.token_id,
        split_time=0.4,
    )

    operation.apply(recording)
    intervals = recording.get_tier("phones").intervals

    assert len(intervals) == 2
    assert [item.start for item in intervals] == [0.0, 0.4]
    assert [item.end for item in intervals] == [0.4, 1.0]


def test_split_interval_operation_undo_restores_original_interval() -> None:
    """Split operations support undo."""
    interval = Interval(start=0.0, end=1.0, label="aa")
    recording = Recording(id="rec-1", tiers={"phones": Tier(name="phones", intervals=[interval])})
    operation = SplitIntervalOperation(
        tier_name="phones",
        token_id=interval.token_id,
        split_time=0.4,
    )

    operation.apply(recording)
    operation.undo(recording)
    intervals = recording.get_tier("phones").intervals

    assert len(intervals) == 1
    assert intervals[0].token_id == interval.token_id
    assert intervals[0].start == 0.0
    assert intervals[0].end == 1.0
