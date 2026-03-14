"""Batch operation tests."""

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.operations.batch import BatchReplaceOperation
from movak.operations.relabel import RelabelOperation


def test_batch_replace_operation_applies_multiple_operations() -> None:
    """Batch operations apply each operation in sequence."""
    first = Interval(start=0.0, end=0.2, label="a")
    second = Interval(start=0.2, end=0.4, label="b")
    recording = Recording(
        id="rec-1",
        tiers={"phones": Tier(name="phones", intervals=[first, second])},
    )
    operation = BatchReplaceOperation(
        operations=[
            RelabelOperation(tier_name="phones", token_id=first.token_id, new_label="x"),
            RelabelOperation(tier_name="phones", token_id=second.token_id, new_label="y"),
        ]
    )

    operation.apply(recording)

    assert [interval.label for interval in recording.get_tier("phones").intervals] == ["x", "y"]
