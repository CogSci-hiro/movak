"""Merge operation tests."""

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.operations.merge import MergeIntervalOperation


def test_merge_interval_operation_combines_contiguous_intervals() -> None:
    """Merge operations combine adjacent intervals."""
    left = Interval(start=0.0, end=0.5, label="a")
    right = Interval(start=0.5, end=1.0, label="b")
    recording = Recording(id="rec-1", tiers={"phones": Tier(name="phones", intervals=[left, right])})
    operation = MergeIntervalOperation(
        tier_name="phones",
        left_token_id=left.token_id,
        right_token_id=right.token_id,
        merged_label="ab",
    )

    operation.apply(recording)
    intervals = recording.get_tier("phones").intervals

    assert len(intervals) == 1
    assert intervals[0].label == "ab"
    assert intervals[0].start == 0.0
    assert intervals[0].end == 1.0


def test_merge_interval_operation_undo_restores_original_intervals() -> None:
    """Merge operations support undo."""
    left = Interval(start=0.0, end=0.5, label="a")
    right = Interval(start=0.5, end=1.0, label="b")
    recording = Recording(id="rec-1", tiers={"phones": Tier(name="phones", intervals=[left, right])})
    operation = MergeIntervalOperation(
        tier_name="phones",
        left_token_id=left.token_id,
        right_token_id=right.token_id,
    )

    operation.apply(recording)
    operation.undo(recording)

    assert [interval.token_id for interval in recording.get_tier("phones").intervals] == [
        left.token_id,
        right.token_id,
    ]
