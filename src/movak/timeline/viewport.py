"""Timeline viewport primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

MIN_VISIBLE_DURATION = 0.01
DEFAULT_VISIBLE_DURATION = 10.0
DEFAULT_VIEWPORT_WIDTH_PIXELS = 1000

ViewportListener = Callable[["TimelineViewport"], None]


@dataclass(slots=True)
class TimelineViewport:
    """Represent the visible timeline span and coordinate redraws.

    Parameters
    ----------
    visible_start_time
        Visible start time in seconds.
    visible_end_time
        Visible end time in seconds.
    pixels_per_second
        Horizontal zoom expressed as pixels per second.
    total_duration
        Total available duration in seconds.
    """

    visible_start_time: float = 0.0
    visible_end_time: float = DEFAULT_VISIBLE_DURATION
    pixels_per_second: float = DEFAULT_VIEWPORT_WIDTH_PIXELS / DEFAULT_VISIBLE_DURATION
    total_duration: float | None = None
    _listeners: list[ViewportListener] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate the initial viewport configuration."""

        self.set_viewport(self.visible_start_time, self.visible_end_time, notify=False)

    @property
    def visible_duration(self) -> float:
        """Return the currently visible duration in seconds."""

        return self.visible_end_time - self.visible_start_time

    def set_viewport(self, start_time: float, end_time: float, *, notify: bool = True) -> None:
        """Set the visible time range.

        Parameters
        ----------
        start_time
            Visible start time in seconds.
        end_time
            Visible end time in seconds.
        notify
            Whether registered listeners should be notified.
        """

        if end_time <= start_time:
            raise ValueError("Viewport end_time must be greater than start_time.")

        visible_duration = max(end_time - start_time, MIN_VISIBLE_DURATION)
        clamped_start = max(start_time, 0.0)
        clamped_end = clamped_start + visible_duration

        if self.total_duration is not None:
            max_start_time = max(self.total_duration - visible_duration, 0.0)
            clamped_start = min(clamped_start, max_start_time)
            clamped_end = min(clamped_start + visible_duration, self.total_duration)

        self.visible_start_time = clamped_start
        self.visible_end_time = clamped_end

        if notify:
            self._notify_listeners()

    def zoom(self, factor: float, *, anchor_time: float | None = None) -> None:
        """Zoom the viewport around an anchor time.

        Parameters
        ----------
        factor
            Multiplicative zoom factor. Values greater than 1 zoom in.
        anchor_time
            Optional anchor time that remains visually stable during zoom.
        """

        if factor <= 0.0:
            raise ValueError("Zoom factor must be positive.")

        current_duration = self.visible_duration
        new_duration = max(current_duration / factor, MIN_VISIBLE_DURATION)
        center_time = anchor_time if anchor_time is not None else (self.visible_start_time + current_duration / 2.0)

        new_start_time = center_time - (new_duration / 2.0)
        new_end_time = center_time + (new_duration / 2.0)

        self.pixels_per_second *= factor
        self.set_viewport(new_start_time, new_end_time)

    def scroll(self, delta_time: float) -> None:
        """Pan the viewport horizontally.

        Parameters
        ----------
        delta_time
            Horizontal offset in seconds.
        """

        self.set_viewport(
            self.visible_start_time + delta_time,
            self.visible_end_time + delta_time,
        )

    def time_to_pixel(self, time_value: float) -> float:
        """Convert a time value to a pixel offset within the viewport."""

        return (time_value - self.visible_start_time) * self.pixels_per_second

    def pixel_to_time(self, pixel_value: float) -> float:
        """Convert a viewport pixel offset to time."""

        return self.visible_start_time + (pixel_value / self.pixels_per_second)

    def add_listener(self, listener: ViewportListener) -> None:
        """Register a callback for viewport changes."""

        self._listeners.append(listener)

    def remove_listener(self, listener: ViewportListener) -> None:
        """Remove a previously registered viewport callback."""

        self._listeners = [item for item in self._listeners if item is not listener]

    def _notify_listeners(self) -> None:
        """Notify listeners that the viewport has changed."""

        for listener in tuple(self._listeners):
            listener(self)


Viewport = TimelineViewport
