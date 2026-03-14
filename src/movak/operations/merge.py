"""Merge operations."""

from __future__ import annotations

from dataclasses import dataclass

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.operations.base import Operation


@dataclass(slots=True)
class MergeIntervalOperation(Operation):
    """Merge adjacent intervals."""

    tier_name: str
    left_token_id: str
    right_token_id: str
    merged_label: str | None = None
    _left_interval: Interval | None = None
    _right_interval: Interval | None = None
    _merged_token_id: str | None = None

    def apply(self, recording: Recording) -> None:
        """Apply the operation."""
        tier = recording.get_tier(self.tier_name)
        left_interval = tier.find_interval(self.left_token_id)
        right_interval = tier.find_interval(self.right_token_id)
        if left_interval is None or right_interval is None:
            raise KeyError("Both intervals must exist before they can be merged.")
        if left_interval.end != right_interval.start:
            raise ValueError("Only contiguous intervals can be merged.")

        self._left_interval = Interval(
            token_id=left_interval.token_id,
            start=left_interval.start,
            end=left_interval.end,
            label=left_interval.label,
            confidence=left_interval.confidence,
            metadata=dict(left_interval.metadata),
        )
        self._right_interval = Interval(
            token_id=right_interval.token_id,
            start=right_interval.start,
            end=right_interval.end,
            label=right_interval.label,
            confidence=right_interval.confidence,
            metadata=dict(right_interval.metadata),
        )

        tier.remove_interval(self.left_token_id)
        tier.remove_interval(self.right_token_id)
        merged_interval = Interval(
            start=self._left_interval.start,
            end=self._right_interval.end,
            label=self._left_interval.label if self.merged_label is None else self.merged_label,
            confidence=self._left_interval.confidence,
            metadata=dict(self._left_interval.metadata),
        )
        self._merged_token_id = merged_interval.token_id
        tier.add_interval(merged_interval)

    def undo(self, recording: Recording) -> None:
        """Undo the operation."""
        if (
            self._left_interval is None
            or self._right_interval is None
            or self._merged_token_id is None
        ):
            raise RuntimeError("Cannot undo an operation that has not been applied.")

        tier = recording.get_tier(self.tier_name)
        tier.remove_interval(self._merged_token_id)
        tier.add_interval(
            Interval(
                token_id=self._left_interval.token_id,
                start=self._left_interval.start,
                end=self._left_interval.end,
                label=self._left_interval.label,
                confidence=self._left_interval.confidence,
                metadata=dict(self._left_interval.metadata),
            )
        )
        tier.add_interval(
            Interval(
                token_id=self._right_interval.token_id,
                start=self._right_interval.start,
                end=self._right_interval.end,
                label=self._right_interval.label,
                confidence=self._right_interval.confidence,
                metadata=dict(self._right_interval.metadata),
            )
        )
