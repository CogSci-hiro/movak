"""Tier model."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field

from movak.core.interval import Interval


@dataclass(slots=True)
class Tier:
    """Ordered annotation tier.

    Parameters
    ----------
    name
        Tier name.
    intervals
        Ordered interval list.
    parent_tier
        Optional parent tier name.
    """

    name: str
    intervals: list[Interval] = field(default_factory=list)
    parent_tier: str | None = None

    def __post_init__(self) -> None:
        """Normalize interval ordering after initialization."""
        self.intervals.sort(key=lambda interval: (interval.start, interval.end, interval.token_id))

    def add_interval(self, interval: Interval) -> None:
        """Add an interval while preserving sort order.

        Parameters
        ----------
        interval
            Interval to insert.
        """
        insert_keys = [(item.start, item.end, item.token_id) for item in self.intervals]
        interval_key = (interval.start, interval.end, interval.token_id)
        insert_index = bisect_left(insert_keys, interval_key)
        self.intervals.insert(insert_index, interval)

    def remove_interval(self, token_id: str) -> Interval:
        """Remove an interval by token identifier.

        Parameters
        ----------
        token_id
            Interval token identifier.

        Returns
        -------
        Interval
            Removed interval.

        Raises
        ------
        KeyError
            Raised when no matching interval exists.
        """
        for index, interval in enumerate(self.intervals):
            if interval.token_id == token_id:
                return self.intervals.pop(index)
        raise KeyError(f"Interval '{token_id}' does not exist in tier '{self.name}'.")

    def find_interval(self, token_id: str) -> Interval | None:
        """Find an interval by token identifier.

        Parameters
        ----------
        token_id
            Interval token identifier.

        Returns
        -------
        Interval | None
            Matching interval, or ``None`` when it is absent.
        """
        for interval in self.intervals:
            if interval.token_id == token_id:
                return interval
        return None

    def get_intervals_in_range(self, start: float, end: float) -> list[Interval]:
        """Return intervals overlapping a time range.

        Parameters
        ----------
        start
            Range start in seconds.
        end
            Range end in seconds.

        Returns
        -------
        list[Interval]
            Intervals that overlap the range.
        """
        if end < start:
            raise ValueError("Range end must be greater than or equal to start.")
        return [
            interval
            for interval in self.intervals
            if interval.start < end and start < interval.end
        ]
