"""Playback controller placeholders."""

from __future__ import annotations


class PlaybackController:
    """Coordinate application playback behavior."""

    def play_selection(self) -> None:
        """Play the current selection."""
        pass

    def stop(self) -> None:
        """Stop active playback."""
        pass
