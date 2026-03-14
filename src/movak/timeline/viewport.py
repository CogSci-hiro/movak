"""Timeline viewport placeholders."""

from __future__ import annotations


class Viewport:
    """Represent the visible timeline span."""

    def set_range(self, start_time: float, end_time: float) -> None:
        """Set the viewport time range.

        Parameters
        ----------
        start_time
            Start time in seconds.
        end_time
            End time in seconds.
        """
        pass
