"""Split operations."""

from __future__ import annotations

from dataclasses import dataclass

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.operations.base import Operation


@dataclass(slots=True)
class SplitIntervalOperation(Operation):
    """Split an interval into two parts."""

    tier_name: str
    token_id: str
    split_time: float
    right_label: str | None = None
    _original_interval: Interval | None = None
    _left_token_id: str | None = None
    _right_token_id: str | None = None

    def apply(self, recording: Recording) -> None:
        """Apply the operation."""
        tier = recording.get_tier(self.tier_name)
        interval = tier.find_interval(self.token_id)
        if interval is None:
            raise KeyError(f"Interval '{self.token_id}' does not exist.")
        if not interval.start < self.split_time < interval.end:
            raise ValueError("Split time must fall strictly inside the interval.")

        self._original_interval = Interval(
            token_id=interval.token_id,
            start=interval.start,
            end=interval.end,
            label=interval.label,
            confidence=interval.confidence,
            metadata=dict(interval.metadata),
        )
        tier.remove_interval(self.token_id)

        left_interval = Interval(
            token_id=interval.token_id,
            start=interval.start,
            end=self.split_time,
            label=interval.label,
            confidence=interval.confidence,
            metadata=dict(interval.metadata),
        )
        right_interval = Interval(
            start=self.split_time,
            end=interval.end,
            label=interval.label if self.right_label is None else self.right_label,
            confidence=interval.confidence,
            metadata=dict(interval.metadata),
        )

        self._left_token_id = left_interval.token_id
        self._right_token_id = right_interval.token_id
        tier.add_interval(left_interval)
        tier.add_interval(right_interval)

    def undo(self, recording: Recording) -> None:
        """Undo the operation."""
        if self._original_interval is None or self._left_token_id is None or self._right_token_id is None:
            raise RuntimeError("Cannot undo an operation that has not been applied.")

        tier = recording.get_tier(self.tier_name)
        tier.remove_interval(self._left_token_id)
        tier.remove_interval(self._right_token_id)
        tier.add_interval(
            Interval(
                token_id=self._original_interval.token_id,
                start=self._original_interval.start,
                end=self._original_interval.end,
                label=self._original_interval.label,
                confidence=self._original_interval.confidence,
                metadata=dict(self._original_interval.metadata),
            )
        )
