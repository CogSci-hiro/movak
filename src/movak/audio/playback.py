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
        self._loop_enabled = False
        self._loop_start_ms: int | None = None
        self._loop_end_ms: int | None = None

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

    @property
    def loop_enabled(self) -> bool:
        """Return whether loop playback is enabled."""
        return self._loop_enabled

    @property
    def loop_range_ms(self) -> tuple[int, int] | None:
        """Return the active loop range, if one exists."""
        if self._loop_start_ms is None or self._loop_end_ms is None:
            return None
        return self._loop_start_ms, self._loop_end_ms

    def load_file(self, path: str) -> None:
        """Load a local audio file into the media player."""
        self._current_path = path
        self.clear_loop_range()
        self._set_error_message("")
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(path))
        self.source_changed.emit(self.current_file_name)
        self.position_changed.emit(self.position_ms)
        self.duration_changed.emit(self.duration_ms)

    def play(self) -> None:
        """Start playback."""
        if self._should_seek_to_loop_start(self.position_ms):
            self.player.setPosition(self._loop_start_ms or 0)
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

    def set_playback_rate(self, playback_rate: float) -> None:
        """Set playback speed using a normalized multiplier."""
        self.player.setPlaybackRate(max(playback_rate, 0.1))

    def set_loop_enabled(self, enabled: bool) -> None:
        """Enable or disable loop playback."""
        self._loop_enabled = enabled

    def set_loop_range_ms(self, start_ms: int, end_ms: int) -> None:
        """Set the active loop playback range."""
        normalized_start_ms = max(0, min(start_ms, end_ms))
        normalized_end_ms = max(normalized_start_ms, max(start_ms, end_ms))
        if normalized_end_ms <= normalized_start_ms:
            self.clear_loop_range()
            return
        self._loop_start_ms = normalized_start_ms
        self._loop_end_ms = normalized_end_ms

    def clear_loop_range(self) -> None:
        """Clear the active loop range."""
        self._loop_start_ms = None
        self._loop_end_ms = None

    def _on_position_changed(self, position_ms: int) -> None:
        if self._should_wrap_loop(position_ms):
            self.player.setPosition(self._loop_start_ms or 0)
            return
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

    def _should_wrap_loop(self, position_ms: int) -> bool:
        if not self._loop_enabled:
            return False
        if self.playback_state != QMediaPlayer.PlaybackState.PlayingState:
            return False
        if self._loop_start_ms is None or self._loop_end_ms is None:
            return False
        return position_ms >= self._loop_end_ms

    def _should_seek_to_loop_start(self, position_ms: int) -> bool:
        if not self._loop_enabled:
            return False
        if self._loop_start_ms is None or self._loop_end_ms is None:
            return False
        return position_ms < self._loop_start_ms or position_ms >= self._loop_end_ms
