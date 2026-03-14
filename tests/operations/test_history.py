"""Operation history tests."""

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.history.history import OperationHistory
from movak.operations.relabel import RelabelOperation


def test_operation_history_supports_undo_and_redo() -> None:
    """History tracks applied operations."""
    interval = Interval(start=0.0, end=0.5, label="a")
    recording = Recording(id="rec-1", tiers={"phones": Tier(name="phones", intervals=[interval])})
    history = OperationHistory()
    operation = RelabelOperation(tier_name="phones", token_id=interval.token_id, new_label="b")

    history.apply_operation(recording, operation)
    assert interval.label == "b"

    history.undo(recording)
    assert interval.label == "a"

    history.redo(recording)
    assert interval.label == "b"
