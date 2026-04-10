from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QFileDialog, QDialog, QWidget

from ...audio.loader import OPEN_AUDIO_DIALOG_FILTER, load_audio_for_waveform, normalize_local_audio_path
from ...audio.playback import AudioPlaybackService, format_milliseconds
from ...audio.spectrogram import SpectrogramSettings, build_spectrogram
from ...audio.waveform_cache import WaveformCache, WaveformData
from ..components.spectrogram_settings_dialog import SpectrogramSettingsDialog

NO_AUDIO_LOADED_LABEL = "No audio loaded"
FILE_DIALOG_CAPTION = "Open audio"
STATUS_MESSAGE_TIMEOUT_MS = 5_000


class TransportBarView(Protocol):
    """Minimal transport bar surface needed by the playback controller."""

    open_requested: object
    play_pause_requested: object
    stop_requested: object
    waveform_display_mode_requested: object

    def set_source_label(self, text: str) -> None: ...
    def set_position_text(self, text: str) -> None: ...
    def set_duration_text(self, text: str) -> None: ...
    def set_is_playing(self, is_playing: bool) -> None: ...
    def set_waveform_mode_availability(self, stereo_available: bool) -> None: ...
    def current_waveform_display_mode(self) -> str: ...


class WaveformView(Protocol):
    """Waveform surface updated by the controller."""

    def set_waveform_data(self, waveform_data: WaveformData) -> None: ...
    def clear_waveform(self) -> None: ...
    def set_display_mode(self, mode: str) -> None: ...


class SpectrogramView(Protocol):
    """Spectrogram surface updated by the controller."""

    settings_requested: object

    def set_spectrogram_data(
        self,
        spectrogram,
        duration: float,
        max_frequency_hz: float | None = None,
        frame_step_seconds: float | None = None,
        frame_start_seconds: float | None = None,
        frame_end_seconds: float | None = None,
    ) -> None: ...
    def clear_spectrogram(self) -> None: ...


class TimelineViewportView(Protocol):
    """Shared timeline viewport surface updated by the controller."""

    time_selected: object

    def set_total_duration(self, total_duration: float) -> None: ...
    def set_cursor_time(self, cursor_time: float) -> None: ...


class PlaybackController(QObject):
    """Bridge file-open and playback actions to playback and waveform views."""

    audio_file_loaded = pyqtSignal(str)

    def __init__(
        self,
        playback_service: AudioPlaybackService,
        transport_bar: TransportBarView,
        waveform_cache: WaveformCache,
        waveform_view: WaveformView,
        spectrogram_view: SpectrogramView,
        timeline_viewport: TimelineViewportView,
        *,
        dialog_parent: QWidget | None = None,
        file_picker: Callable[[QWidget | None, str, str, str], tuple[str, str]] | None = None,
        status_message_sink: Callable[[str, int], None] | None = None,
        spectrogram_settings_dialog_factory: Callable[[SpectrogramSettings, QWidget | None], QDialog] | None = None,
    ) -> None:
        super().__init__(dialog_parent)
        self.playback_service = playback_service
        self.transport_bar = transport_bar
        self.waveform_cache = waveform_cache
        self.waveform_view = waveform_view
        self.spectrogram_view = spectrogram_view
        self.timeline_viewport = timeline_viewport
        self.dialog_parent = dialog_parent
        self.file_picker = file_picker or QFileDialog.getOpenFileName
        self.status_message_sink = status_message_sink
        self.spectrogram_settings_dialog_factory = spectrogram_settings_dialog_factory or (
            lambda settings, parent: SpectrogramSettingsDialog(settings, parent)
        )
        self.spectrogram_settings = SpectrogramSettings()

        self.transport_bar.open_requested.connect(self.open_audio_file)
        self.transport_bar.play_pause_requested.connect(self.toggle_play_pause)
        self.transport_bar.stop_requested.connect(self.stop)
        self.transport_bar.waveform_display_mode_requested.connect(self._set_waveform_display_mode)
        self.spectrogram_view.settings_requested.connect(self.open_spectrogram_settings)
        self.timeline_viewport.time_selected.connect(self.seek_to_time)

        self.playback_service.source_changed.connect(self._update_source_label)
        self.playback_service.position_changed.connect(self._update_position_label)
        self.playback_service.position_changed.connect(self._update_playhead_position)
        self.playback_service.duration_changed.connect(self._update_duration_label)
        self.playback_service.playback_state_changed.connect(self._update_playback_state)
        self.playback_service.error_changed.connect(self._handle_error_changed)

        self.transport_bar.set_waveform_mode_availability(False)
        self._refresh_transport_bar()

    def open_audio_file(self) -> None:
        """Prompt for a local audio file and load playback plus waveform state."""
        selected_path, _selected_filter = self.file_picker(
            self.dialog_parent,
            FILE_DIALOG_CAPTION,
            "",
            OPEN_AUDIO_DIALOG_FILTER,
        )
        if not selected_path:
            return
        self.open_audio_path(selected_path)

    def open_audio_path(self, selected_path: str) -> bool:
        """Load a known local audio path without showing the file picker.

        Parameters
        ----------
        selected_path:
            Local audio path selected by the user or session restore.

        Returns
        -------
        bool
            ``True`` when the file was loaded successfully.
        """

        try:
            normalized_path = normalize_local_audio_path(selected_path)
            waveform_data = self.waveform_cache.set_waveform(load_audio_for_waveform(normalized_path))
            self.waveform_view.set_waveform_data(waveform_data)
            spectrogram_data = build_spectrogram(
                waveform_data.samples,
                waveform_data.sample_rate,
                settings=self.spectrogram_settings,
            )
            max_frequency_hz = float(spectrogram_data.frequency_hz[-1]) if spectrogram_data.frequency_hz.size else None
            self.spectrogram_view.set_spectrogram_data(
                spectrogram_data.magnitude,
                spectrogram_data.duration_seconds,
                max_frequency_hz,
                spectrogram_data.frame_step_seconds,
                spectrogram_data.frame_start_seconds,
                spectrogram_data.frame_end_seconds,
            )
            self.transport_bar.set_waveform_mode_availability(waveform_data.channel_count >= 2)
            self._set_waveform_display_mode(self.transport_bar.current_waveform_display_mode())
            self.timeline_viewport.set_total_duration(max(waveform_data.duration_seconds, 0.05))
            self.timeline_viewport.set_cursor_time(0.0)
            self.playback_service.load_file(normalized_path)
        except (RuntimeError, ValueError, OSError) as error:
            self.waveform_cache.clear()
            self.waveform_view.clear_waveform()
            self.spectrogram_view.clear_spectrogram()
            self.waveform_view.set_display_mode("mono")
            self.transport_bar.set_waveform_mode_availability(False)
            self.timeline_viewport.set_total_duration(12.0)
            self.timeline_viewport.set_cursor_time(0.0)
            self._show_status_message(f"Failed to load audio: {error}")
            return False

        self._show_status_message(f"Loaded audio: {self.playback_service.current_file_name}")
        self.audio_file_loaded.emit(normalized_path)
        return True

    def open_spectrogram_settings(self) -> None:
        """Open the spectrogram settings dialog and rebuild if accepted."""
        dialog = self.spectrogram_settings_dialog_factory(self.spectrogram_settings, self.dialog_parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not hasattr(dialog, "settings"):
            return
        self.spectrogram_settings = dialog.settings()
        self._refresh_spectrogram()

    def play(self) -> None:
        """Start playback."""
        if not self.playback_service.current_path:
            self._show_status_message("Open an audio file before starting playback.")
            return
        self.playback_service.play()

    def pause(self) -> None:
        """Pause playback."""
        self.playback_service.pause()

    def stop(self) -> None:
        """Stop playback."""
        self.playback_service.stop()

    def toggle_play_pause(self) -> None:
        """Toggle audio playback."""
        if not self.playback_service.current_path:
            self._show_status_message("Open an audio file before starting playback.")
            return
        self.playback_service.toggle_play_pause()

    def seek_to_time(self, time_s: float) -> None:
        """Move playback and the playhead to a specific time."""
        clamped_time = max(time_s, 0.0)
        self.timeline_viewport.set_cursor_time(clamped_time)
        if not self.playback_service.current_path:
            return
        self.playback_service.set_position_ms(int(clamped_time * 1_000.0))

    def _refresh_transport_bar(self) -> None:
        self._update_source_label(self.playback_service.current_file_name)
        self._update_position_label(self.playback_service.position_ms)
        self._update_duration_label(self.playback_service.duration_ms)
        self._update_playback_state(self.playback_service.playback_state)
        self._update_playhead_position(self.playback_service.position_ms)

    def _update_source_label(self, file_name: str) -> None:
        self.transport_bar.set_source_label(file_name or NO_AUDIO_LOADED_LABEL)

    def _update_position_label(self, position_ms: int) -> None:
        self.transport_bar.set_position_text(format_milliseconds(position_ms))

    def _update_duration_label(self, duration_ms: int) -> None:
        self.transport_bar.set_duration_text(format_milliseconds(duration_ms))

    def _update_playback_state(self, playback_state: QMediaPlayer.PlaybackState) -> None:
        self.transport_bar.set_is_playing(playback_state == QMediaPlayer.PlaybackState.PlayingState)

    def _update_playhead_position(self, position_ms: int) -> None:
        self.timeline_viewport.set_cursor_time(position_ms / 1_000.0)

    def _handle_error_changed(self, error_message: str) -> None:
        if error_message:
            self._show_status_message(error_message)

    def _set_waveform_display_mode(self, mode: str) -> None:
        self.waveform_view.set_display_mode(mode)

    def _refresh_spectrogram(self) -> None:
        waveform_data = self.waveform_cache.current_waveform
        if waveform_data is None:
            return
        spectrogram_data = build_spectrogram(
            waveform_data.samples,
            waveform_data.sample_rate,
            settings=self.spectrogram_settings,
        )
        max_frequency_hz = float(spectrogram_data.frequency_hz[-1]) if spectrogram_data.frequency_hz.size else None
        self.spectrogram_view.set_spectrogram_data(
            spectrogram_data.magnitude,
            spectrogram_data.duration_seconds,
            max_frequency_hz,
            spectrogram_data.frame_step_seconds,
            spectrogram_data.frame_start_seconds,
            spectrogram_data.frame_end_seconds,
        )

    def _show_status_message(self, message: str) -> None:
        if self.status_message_sink is None:
            return
        self.status_message_sink(message, STATUS_MESSAGE_TIMEOUT_MS)
