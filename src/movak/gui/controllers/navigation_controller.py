from __future__ import annotations

from typing import Protocol


class TimelineViewportView(Protocol):
    """Viewport surface needed by timeline navigation."""

    total_duration: float
    visible_start_time: float
    visible_end_time: float

    def fit_to_audio(self) -> None: ...
    def center_on_time(self, time_s: float) -> None: ...


class PlaybackStateView(Protocol):
    """Playback state surface needed for recentering on the playhead."""

    position_ms: int


class NavigationController:
    """Coordinate high-level timeline navigation actions."""

    def __init__(self, timeline_viewport: TimelineViewportView, playback_service: PlaybackStateView) -> None:
        self.timeline_viewport = timeline_viewport
        self.playback_service = playback_service

    def fit_to_audio(self) -> None:
        """Show the full loaded audio duration."""
        self.timeline_viewport.fit_to_audio()

    def center_on_playhead(self) -> None:
        """Center the visible range on the current playback position."""
        if self.timeline_viewport.total_duration <= 0.0:
            return
        self.timeline_viewport.center_on_time(self.playback_service.position_ms / 1_000.0)
