"""Boundary operation tests."""

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.operations.boundary import MoveBoundaryOperation


def test_move_boundary_operation_updates_interval_and_undoes() -> None:
    """Boundary moves are reversible."""
    interval = Interval(start=0.0, end=1.0, label="a")
    recording = Recording(id="rec-1", tiers={"phones": Tier(name="phones", intervals=[interval])})
    operation = MoveBoundaryOperation(
        tier_name="phones",
        token_id=interval.token_id,
        boundary="end",
        new_time=0.75,
    )

    operation.apply(recording)
    assert interval.end == 0.75

    operation.undo(recording)
    assert interval.end == 1.0
