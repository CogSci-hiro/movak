"""Qt Multimedia-backed audio playback services."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

DEFAULT_VOLUME = 0.75
MILLISECONDS_PER_SECOND = 1_000
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60


def format_milliseconds(milliseconds: int) -> str:
    """Format a millisecond duration as ``mm:ss`` or ``hh:mm:ss``."""
    if milliseconds <= 0:
        return "00:00"

    total_seconds = milliseconds // MILLISECONDS_PER_SECOND
    minutes, seconds = divmod(total_seconds, SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class AudioPlaybackService(QObject):
    """Own a persistent Qt multimedia player and expose simple playback state."""

    source_changed = pyqtSignal(str)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    playback_state_changed = pyqtSignal(QMediaPlayer.PlaybackState)
    error_changed = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(DEFAULT_VOLUME)

        self._current_path = ""
        self._error_message = ""

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        if hasattr(self.player, "errorOccurred"):
            self.player.errorOccurred.connect(self._on_error_occurred)
        elif hasattr(self.player, "errorChanged"):
            self.player.errorChanged.connect(self._on_error_changed)

    @property
    def current_path(self) -> str:
        """Return the currently loaded local path, if any."""
        return self._current_path

    @property
    def current_file_name(self) -> str:
        """Return the loaded file name, if any."""
        if not self._current_path:
            return ""
        return Path(self._current_path).name

    @property
    def duration_ms(self) -> int:
        """Return the current media duration in milliseconds."""
        return self.player.duration()

    @property
    def position_ms(self) -> int:
        """Return the current playback position in milliseconds."""
        return self.player.position()

    @property
    def playback_state(self) -> QMediaPlayer.PlaybackState:
        """Return the Qt playback state."""
        return self.player.playbackState()

    @property
    def error_message(self) -> str:
        """Return the last reported playback error."""
        return self._error_message

    def load_file(self, path: str) -> None:
        """Load a local audio file into the media player."""
        self._current_path = path
        self._set_error_message("")
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(path))
        self.source_changed.emit(self.current_file_name)
        self.position_changed.emit(self.position_ms)
        self.duration_changed.emit(self.duration_ms)

    def play(self) -> None:
        """Start playback."""
        self.player.play()

    def pause(self) -> None:
        """Pause playback."""
        self.player.pause()

    def stop(self) -> None:
        """Stop playback."""
        self.player.stop()

    def toggle_play_pause(self) -> None:
        """Toggle between playing and paused states."""
        if self.playback_state == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
            return
        self.play()

    def set_position_ms(self, position_ms: int) -> None:
        """Seek to the requested playback position."""
        self.player.setPosition(max(0, position_ms))

    def set_volume(self, volume: float) -> None:
        """Set output volume using a normalized ``0.0`` to ``1.0`` range."""
        self.audio_output.setVolume(min(max(volume, 0.0), 1.0))

    def _on_position_changed(self, position_ms: int) -> None:
        self.position_changed.emit(position_ms)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.duration_changed.emit(duration_ms)

    def _on_playback_state_changed(self, playback_state: QMediaPlayer.PlaybackState) -> None:
        self.playback_state_changed.emit(playback_state)

    def _on_error_occurred(self, _error: QMediaPlayer.Error, error_message: str) -> None:
        self._set_error_message(error_message or "Failed to play audio.")

    def _on_error_changed(self) -> None:
        if self.player.error() == QMediaPlayer.Error.NoError:
            self._set_error_message("")
            return
        self._set_error_message(self.player.errorString() or "Failed to play audio.")

    def _set_error_message(self, error_message: str) -> None:
        if self._error_message == error_message:
            return
        self._error_message = error_message
        self.error_changed.emit(error_message)
