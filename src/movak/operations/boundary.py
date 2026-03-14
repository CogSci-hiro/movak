"""Boundary operations."""

from __future__ import annotations

from dataclasses import dataclass

from movak.core.recording import Recording
from movak.operations.base import Operation


@dataclass(slots=True)
class MoveBoundaryOperation(Operation):
    """Move an interval boundary."""

    tier_name: str
    token_id: str
    boundary: str
    new_time: float
    _previous_time: float | None = None

    def apply(self, recording: Recording) -> None:
        """Apply the operation."""
        interval = recording.get_tier(self.tier_name).find_interval(self.token_id)
        if interval is None:
            raise KeyError(f"Interval '{self.token_id}' does not exist.")

        if self.boundary == "start":
            self._previous_time = interval.start
            interval.set_bounds(start=self.new_time, end=interval.end)
        elif self.boundary == "end":
            self._previous_time = interval.end
            interval.set_bounds(start=interval.start, end=self.new_time)
        else:
            raise ValueError("Boundary must be either 'start' or 'end'.")

        recording.get_tier(self.tier_name).intervals.sort(
            key=lambda item: (item.start, item.end, item.token_id)
        )

    def undo(self, recording: Recording) -> None:
        """Undo the operation."""
        if self._previous_time is None:
            raise RuntimeError("Cannot undo an operation that has not been applied.")

        interval = recording.get_tier(self.tier_name).find_interval(self.token_id)
        if interval is None:
            raise KeyError(f"Interval '{self.token_id}' does not exist.")

        if self.boundary == "start":
            interval.set_bounds(start=self._previous_time, end=interval.end)
        else:
            interval.set_bounds(start=interval.start, end=self._previous_time)

        recording.get_tier(self.tier_name).intervals.sort(
            key=lambda item: (item.start, item.end, item.token_id)
        )
