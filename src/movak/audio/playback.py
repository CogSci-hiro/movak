"""Audio playback placeholders."""

from __future__ import annotations


class AudioPlayback:
    """Control low-level audio playback."""

    def play(self) -> None:
        """Start playback."""
        pass

    def stop(self) -> None:
        """Stop playback."""
        pass
