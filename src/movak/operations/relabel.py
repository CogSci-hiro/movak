"""Relabel operations."""

from __future__ import annotations

from dataclasses import dataclass

from movak.core.recording import Recording
from movak.operations.base import Operation


@dataclass(slots=True)
class RelabelOperation(Operation):
    """Change an interval label."""

    tier_name: str
    token_id: str
    new_label: str
    _previous_label: str | None = None

    def apply(self, recording: Recording) -> None:
        """Apply the operation."""
        interval = recording.get_tier(self.tier_name).find_interval(self.token_id)
        if interval is None:
            raise KeyError(f"Interval '{self.token_id}' does not exist.")
        self._previous_label = interval.label
        interval.relabel(self.new_label)

    def undo(self, recording: Recording) -> None:
        """Undo the operation."""
        if self._previous_label is None:
            raise RuntimeError("Cannot undo an operation that has not been applied.")

        interval = recording.get_tier(self.tier_name).find_interval(self.token_id)
        if interval is None:
            raise KeyError(f"Interval '{self.token_id}' does not exist.")
        interval.relabel(self._previous_label)
