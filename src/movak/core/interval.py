"""Interval model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Interval:
    """Single annotation interval.

    Parameters
    ----------
    start
        Interval start time in seconds.
    end
        Interval end time in seconds.
    label
        Interval label text.
    token_id
        Unique token identifier.
    confidence
        Optional confidence score for automatic annotations.
    metadata
        Arbitrary interval metadata.
    """

    start: float
    end: float
    label: str = ""
    token_id: str = field(default_factory=lambda: str(uuid4()))
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate interval bounds after initialization."""
        self._validate_bounds(self.start, self.end)

    @staticmethod
    def _validate_bounds(start: float, end: float) -> None:
        """Validate interval bounds.

        Parameters
        ----------
        start
            Proposed start time.
        end
            Proposed end time.

        Raises
        ------
        ValueError
            Raised when the interval bounds are invalid.
        """
        if start < 0.0:
            raise ValueError("Interval start must be non-negative.")
        if end < start:
            raise ValueError("Interval end must be greater than or equal to start.")

    def duration(self) -> float:
        """Return interval duration.

        Returns
        -------
        float
            Interval duration in seconds.
        """
        return self.end - self.start

    def overlaps(self, other: Interval) -> bool:
        """Return whether this interval overlaps another interval.

        Parameters
        ----------
        other
            Interval to compare against.

        Returns
        -------
        bool
            ``True`` when the intervals overlap, otherwise ``False``.
        """
        return self.start < other.end and other.start < self.end

    def contains(self, time: float) -> bool:
        """Return whether the interval contains a time point.

        Parameters
        ----------
        time
            Time point in seconds.

        Returns
        -------
        bool
            ``True`` when the interval contains the time point.
        """
        return self.start <= time <= self.end

    def relabel(self, label: str) -> None:
        """Update the interval label.

        Parameters
        ----------
        label
            New label value.
        """
        self.label = label

    def set_bounds(self, start: float, end: float) -> None:
        """Update interval bounds.

        Parameters
        ----------
        start
            New start time in seconds.
        end
            New end time in seconds.
        """
        self._validate_bounds(start, end)
        self.start = start
        self.end = end
