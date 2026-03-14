"""Relabel operation tests."""

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.operations.relabel import RelabelOperation


def test_relabel_operation_changes_label_and_undoes() -> None:
    """Relabel operations are reversible."""
    interval = Interval(start=0.0, end=0.5, label="a")
    recording = Recording(id="rec-1", tiers={"phones": Tier(name="phones", intervals=[interval])})
    operation = RelabelOperation(
        tier_name="phones",
        token_id=interval.token_id,
        new_label="b",
    )

    operation.apply(recording)
    assert interval.label == "b"

    operation.undo(recording)
    assert interval.label == "a"
