from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import sys
import tempfile
from typing import Protocol

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QFileDialog, QDialog, QWidget

from ...audio.loader import OPEN_AUDIO_DIALOG_FILTER, load_audio_for_waveform, normalize_local_audio_path
from ...audio.playback import AudioPlaybackService, format_milliseconds
from ...audio.spectrogram import SpectrogramSettings, build_spectrogram
from ...audio.waveform_cache import WaveformCache, WaveformData
from ...features.formants import FormantSettings, build_formant_tracks
from ..components.spectrogram_settings_dialog import SpectrogramSettingsDialog

NO_AUDIO_LOADED_LABEL = "No audio loaded"
FILE_DIALOG_CAPTION = "Open audio"
STATUS_MESSAGE_TIMEOUT_MS = 5_000
FORMANT_VIEW_BUFFER_RATIO = 0.25
FORMANT_MIN_BUFFER_SECONDS = 0.05
FORMANT_MAX_BUFFER_SECONDS = 0.5
FORMANT_CACHE_TILE_SECONDS = 1.0
FORMANT_IDLE_PREFETCH_DELAY_MS = 250


@dataclass(slots=True)
class _CachedFormantTile:
    audio_revision: int
    settings_key: tuple[float, int, float, float, float]
    tile_start_time: float
    tile_end_time: float
    times_seconds: np.ndarray
    frequencies_hz: np.ndarray
    frame_confidence: np.ndarray


@dataclass(slots=True)
class _FormantRequest:
    audio_revision: int
    settings_key: tuple[float, int, float, float, float]
    window_start_time: float
    window_end_time: float
    sample_rate: int
    sample_offset_seconds: float
    samples: np.ndarray

    @property
    def cache_key(self) -> tuple[int, tuple[float, int, float, float, float], int, int]:
        return (
            self.audio_revision,
            self.settings_key,
            int(round(self.window_start_time * 1_000_000.0)),
            int(round(self.window_end_time * 1_000_000.0)),
        )


@dataclass(slots=True)
class _FormantResult:
    request: _FormantRequest
    times_seconds: np.ndarray | None = None
    frequencies_hz: np.ndarray | None = None
    frame_confidence: np.ndarray | None = None
    error_message: str | None = None


def _compute_formants_for_request(request: _FormantRequest) -> _FormantResult:
    try:
        formant_tracks = build_formant_tracks(
            request.samples,
            request.sample_rate,
            settings=FormantSettings(
                time_step_s=request.settings_key[0],
                max_number_of_formants=request.settings_key[1],
                max_frequency_hz=request.settings_key[2],
                window_length_s=request.settings_key[3],
                preemphasis_from_hz=request.settings_key[4],
            ),
        )
    except Exception as error:
        return _FormantResult(request=request, error_message=str(error))
    return _FormantResult(
        request=request,
        times_seconds=formant_tracks.times_seconds + request.sample_offset_seconds,
        frequencies_hz=formant_tracks.frequencies_hz,
        frame_confidence=formant_tracks.frame_confidence,
    )


def _compute_formants_for_request_isolated(request: _FormantRequest) -> _FormantResult:
    worker_module = "movak.features.formant_worker"
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[3])
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else os.pathsep.join((src_path, existing_pythonpath))

    input_file = tempfile.NamedTemporaryFile(prefix="movak-formants-in-", suffix=".npz", delete=False)
    output_file = tempfile.NamedTemporaryFile(prefix="movak-formants-out-", suffix=".npz", delete=False)
    input_file.close()
    output_file.close()
    try:
        np.savez_compressed(
            input_file.name,
            samples=request.samples,
            sample_rate=np.array([request.sample_rate], dtype=np.int32),
            sample_offset_seconds=np.array([request.sample_offset_seconds], dtype=np.float32),
            settings_key=np.array(request.settings_key, dtype=np.float64),
        )
        completed = subprocess.run(
            [sys.executable, "-m", worker_module, input_file.name, output_file.name],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"Formant worker failed with code {completed.returncode}."
            return _compute_formants_for_request(request) if message else _compute_formants_for_request(request)

        with np.load(output_file.name, allow_pickle=False) as payload:
            if int(payload["ok"][0]) == 0:
                error_message = str(payload["error_message"][0])
                return _compute_formants_for_request(request) if error_message else _compute_formants_for_request(request)
            return _FormantResult(
                request=request,
                times_seconds=payload["times_seconds"].astype(np.float32, copy=False),
                frequencies_hz=payload["frequencies_hz"].astype(np.float32, copy=False),
                frame_confidence=payload["frame_confidence"].astype(np.float32, copy=False),
            )
    except Exception:
        return _compute_formants_for_request(request)
    finally:
        for path in (input_file.name, output_file.name):
            try:
                os.unlink(path)
            except OSError:
                pass


class TransportBarView(Protocol):
    """Minimal transport bar surface needed by the playback controller."""

    open_requested: object
    play_pause_requested: object
    stop_requested: object
    loop_toggled: object
    playback_rate_requested: object
    waveform_display_mode_requested: object

    def set_source_label(self, text: str) -> None: ...
    def set_position_text(self, text: str) -> None: ...
    def set_duration_text(self, text: str) -> None: ...
    def set_is_playing(self, is_playing: bool) -> None: ...
    def set_waveform_mode_availability(self, stereo_available: bool) -> None: ...
    def current_waveform_display_mode(self) -> str: ...
    def is_loop_enabled(self) -> bool: ...
    def current_playback_rate(self) -> float: ...


class WaveformView(Protocol):
    """Waveform surface updated by the controller."""

    def set_waveform_data(self, waveform_data: WaveformData) -> None: ...
    def clear_waveform(self) -> None: ...
    def set_display_mode(self, mode: str) -> None: ...


class SpectrogramView(Protocol):
    """Spectrogram surface updated by the controller."""

    settings_requested: object
    point_selected: object
    region_selected: object

    def set_spectrogram_data(
        self,
        spectrogram,
        duration: float,
        max_frequency_hz: float | None = None,
        frame_step_seconds: float | None = None,
        frame_start_seconds: float | None = None,
        frame_end_seconds: float | None = None,
    ) -> None: ...
    def set_formant_data(self, times_seconds, frequencies_hz, frame_confidence=None) -> None: ...
    def clear_formants(self) -> None: ...
    def clear_spectrogram(self) -> None: ...


class TimelineViewportView(Protocol):
    """Shared timeline viewport surface updated by the controller."""

    time_selected: object
    visible_range_changed: object

    def set_total_duration(self, total_duration: float) -> None: ...
    def set_cursor_time(self, cursor_time: float) -> None: ...


class PlaybackController(QObject):
    """Bridge file-open and playback actions to playback and waveform views."""

    audio_file_loaded = pyqtSignal(str)
    formant_analysis_completed = pyqtSignal(object)

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
        self._formant_executor: ThreadPoolExecutor | None = None
        self._formant_refresh_timer = None
        self._formant_idle_prefetch_timer = None
        self._formant_cache: dict[tuple[int, tuple[float, int, float, float, float], int, int], _CachedFormantTile] = {}
        self._inflight_formant_requests: dict[tuple[int, tuple[float, int, float, float, float], int, int], _FormantRequest] = {}
        self._queued_formant_requests: dict[tuple[int, tuple[float, int, float, float, float], int, int], tuple[tuple[int, float], _FormantRequest]] = {}
        self._active_formant_request_key: tuple[int, tuple[float, int, float, float, float], int, int] | None = None
        self._current_formant_window: tuple[float, float] | None = None
        self._current_audio_revision = 0

        self.transport_bar.open_requested.connect(self.open_audio_file)
        self.transport_bar.play_pause_requested.connect(self.toggle_play_pause)
        self.transport_bar.stop_requested.connect(self.stop)
        self.transport_bar.loop_toggled.connect(self._set_loop_enabled)
        self.transport_bar.playback_rate_requested.connect(self._set_playback_rate)
        self.transport_bar.waveform_display_mode_requested.connect(self._set_waveform_display_mode)
        self.spectrogram_view.settings_requested.connect(self.open_spectrogram_settings)
        self.spectrogram_view.point_selected.connect(self._clear_loop_range)
        self.spectrogram_view.region_selected.connect(self._set_loop_range_from_selection)
        self.timeline_viewport.time_selected.connect(self.seek_to_time)
        self.timeline_viewport.visible_range_changed.connect(self._schedule_formant_refresh)

        self.playback_service.source_changed.connect(self._update_source_label)
        self.playback_service.position_changed.connect(self._update_position_label)
        self.playback_service.position_changed.connect(self._update_playhead_position)
        self.playback_service.duration_changed.connect(self._update_duration_label)
        self.playback_service.playback_state_changed.connect(self._update_playback_state)
        self.playback_service.error_changed.connect(self._handle_error_changed)
        self.formant_analysis_completed.connect(self._handle_formant_analysis_completed)
        self.destroyed.connect(self._shutdown_formant_executor)

        self.transport_bar.set_waveform_mode_availability(False)
        self.playback_service.set_loop_enabled(self.transport_bar.is_loop_enabled())
        self.playback_service.set_playback_rate(self.transport_bar.current_playback_rate())
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
            self._invalidate_formant_cache()
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
            self._refresh_formants_for_waveform(waveform_data)
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
        self._invalidate_formant_cache()
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

    def _set_loop_enabled(self, enabled: bool) -> None:
        self.playback_service.set_loop_enabled(enabled)

    def _set_playback_rate(self, playback_rate: float) -> None:
        self.playback_service.set_playback_rate(playback_rate)

    def _set_loop_range_from_selection(
        self,
        start_time_seconds: float,
        end_time_seconds: float,
        _low_frequency_hz: float,
        _high_frequency_hz: float,
    ) -> None:
        start_ms = int(round(min(start_time_seconds, end_time_seconds) * 1_000.0))
        end_ms = int(round(max(start_time_seconds, end_time_seconds) * 1_000.0))
        self.playback_service.set_loop_range_ms(start_ms, end_ms)

    def _clear_loop_range(self, *_args) -> None:
        self.playback_service.clear_loop_range()

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
        self._refresh_formants_for_waveform(waveform_data)

    def _schedule_formant_refresh(self, *_args) -> None:
        if self._formant_refresh_timer is None:
            from PyQt6.QtCore import QTimer

            self._formant_refresh_timer = QTimer(self)
            self._formant_refresh_timer.setSingleShot(True)
            self._formant_refresh_timer.timeout.connect(self._refresh_formants)
        self._formant_refresh_timer.start(0)

    def _refresh_formants(self) -> None:
        waveform_data = self.waveform_cache.current_waveform
        if waveform_data is None:
            return
        self._refresh_formants_for_waveform(waveform_data)

    def _refresh_formants_for_waveform(self, waveform_data: WaveformData) -> None:
        if not self.spectrogram_settings.show_formants:
            self.spectrogram_view.clear_formants()
            self._formant_cache.clear()
            self._inflight_formant_requests.clear()
            self._queued_formant_requests.clear()
            self._active_formant_request_key = None
            self._current_formant_window = None
            if self._formant_idle_prefetch_timer is not None:
                self._formant_idle_prefetch_timer.stop()
            return

        window_start_time, window_end_time = self._formant_window_for_visible_range(waveform_data.duration_seconds)
        settings_key = self._current_formant_settings_key()
        self._current_formant_window = (window_start_time, window_end_time)
        all_tiles_ready = self._update_formants_from_cache(
            audio_revision=self._current_audio_revision,
            settings_key=settings_key,
            window_start_time=window_start_time,
            window_end_time=window_end_time,
        )
        self._enqueue_visible_formant_requests(
            waveform_data=waveform_data,
            settings_key=settings_key,
            window_start_time=window_start_time,
            window_end_time=window_end_time,
        )
        self._schedule_idle_formant_prefetch()
        if not all_tiles_ready:
            self._drain_formant_request_queue()

    def _formant_window_for_visible_range(self, duration_seconds: float) -> tuple[float, float]:
        visible_start_time = max(0.0, self.timeline_viewport.visible_start_time)
        visible_end_time = min(duration_seconds, self.timeline_viewport.visible_end_time)
        visible_duration = max(visible_end_time - visible_start_time, 0.0)
        buffer_seconds = min(
            FORMANT_MAX_BUFFER_SECONDS,
            max(FORMANT_MIN_BUFFER_SECONDS, visible_duration * FORMANT_VIEW_BUFFER_RATIO),
        )
        return (
            max(0.0, visible_start_time - buffer_seconds),
            min(duration_seconds, visible_end_time + buffer_seconds),
        )

    def _current_formant_settings_key(self) -> tuple[float, int, float, float, float]:
        return (
            self.spectrogram_settings.time_step_s,
            self.spectrogram_settings.max_number_of_formants,
            self.spectrogram_settings.formant_max_frequency_hz,
            self.spectrogram_settings.formant_window_length_s,
            self.spectrogram_settings.formant_preemphasis_from_hz,
        )

    def _tile_bounds_for_window(self, window_start_time: float, window_end_time: float) -> list[tuple[float, float]]:
        tile_duration = FORMANT_CACHE_TILE_SECONDS
        first_tile_index = int(np.floor(window_start_time / tile_duration))
        last_tile_index = int(np.floor(max(window_end_time - 1e-9, window_start_time) / tile_duration))
        return [
            (tile_index * tile_duration, (tile_index + 1) * tile_duration)
            for tile_index in range(first_tile_index, last_tile_index + 1)
        ]

    def _build_formant_request(
        self,
        *,
        waveform_data: WaveformData,
        settings_key: tuple[float, int, float, float, float],
        window_start_time: float,
        window_end_time: float,
    ) -> _FormantRequest:
        start_index = max(0, int(np.floor(window_start_time * waveform_data.sample_rate)))
        end_index = min(
            waveform_data.sample_count,
            max(start_index + 1, int(np.ceil(window_end_time * waveform_data.sample_rate))),
        )
        return _FormantRequest(
            audio_revision=self._current_audio_revision,
            settings_key=settings_key,
            window_start_time=window_start_time,
            window_end_time=window_end_time,
            sample_rate=waveform_data.sample_rate,
            sample_offset_seconds=start_index / float(waveform_data.sample_rate),
            samples=np.array(waveform_data.samples[start_index:end_index], dtype=np.float32, copy=True),
        )

    def _find_cached_formant_tile(
        self,
        *,
        audio_revision: int,
        settings_key: tuple[float, int, float, float, float],
        tile_start_time: float,
        tile_end_time: float,
    ) -> _CachedFormantTile | None:
        return self._formant_cache.get(
            (
                audio_revision,
                settings_key,
                int(round(tile_start_time * 1_000_000.0)),
                int(round(tile_end_time * 1_000_000.0)),
            )
        )

    def _update_formants_from_cache(
        self,
        *,
        audio_revision: int,
        settings_key: tuple[float, int, float, float, float],
        window_start_time: float,
        window_end_time: float,
    ) -> bool:
        cached_tiles: list[_CachedFormantTile] = []
        missing_tile_found = False
        for tile_start_time, tile_end_time in self._tile_bounds_for_window(window_start_time, window_end_time):
            cached_tile = self._find_cached_formant_tile(
                audio_revision=audio_revision,
                settings_key=settings_key,
                tile_start_time=tile_start_time,
                tile_end_time=tile_end_time,
            )
            if cached_tile is None:
                missing_tile_found = True
                continue
            cached_tiles.append(cached_tile)

        if not cached_tiles:
            if not missing_tile_found:
                self.spectrogram_view.set_formant_data(
                    np.zeros(0, dtype=np.float32),
                    np.zeros((self.spectrogram_settings.max_number_of_formants, 0), dtype=np.float32),
                    np.zeros(0, dtype=np.float32),
                )
                return True
            self.spectrogram_view.clear_formants()
            return False

        times_seconds = np.concatenate([tile.times_seconds for tile in cached_tiles]).astype(np.float32, copy=False)
        frequencies_hz = np.concatenate([tile.frequencies_hz for tile in cached_tiles], axis=1).astype(np.float32, copy=False)
        frame_confidence = np.concatenate([tile.frame_confidence for tile in cached_tiles]).astype(np.float32, copy=False)

        visible_mask = (times_seconds >= window_start_time) & (times_seconds <= window_end_time)
        if not np.any(visible_mask):
            if missing_tile_found:
                self.spectrogram_view.clear_formants()
                return False
            self.spectrogram_view.clear_formants()
            return True

        cropped_times = times_seconds[visible_mask]
        cropped_frequencies = frequencies_hz[:, visible_mask]
        cropped_confidence = frame_confidence[visible_mask]
        unique_mask = np.ones(cropped_times.size, dtype=bool)
        if cropped_times.size > 1:
            unique_mask[1:] = np.diff(cropped_times) > 1e-6
        self.spectrogram_view.set_formant_data(
            cropped_times[unique_mask],
            cropped_frequencies[:, unique_mask],
            cropped_confidence[unique_mask],
        )
        return not missing_tile_found

    def _enqueue_visible_formant_requests(
        self,
        *,
        waveform_data: WaveformData,
        settings_key: tuple[float, int, float, float, float],
        window_start_time: float,
        window_end_time: float,
    ) -> None:
        window_center_time = 0.5 * (window_start_time + window_end_time)
        for tile_start_time, tile_end_time in self._tile_bounds_for_window(window_start_time, window_end_time):
            request = self._build_formant_request(
                waveform_data=waveform_data,
                settings_key=settings_key,
                window_start_time=tile_start_time,
                window_end_time=tile_end_time,
            )
            tile_center_time = 0.5 * (tile_start_time + tile_end_time)
            self._queue_formant_request(
                request,
                priority=(0, abs(tile_center_time - window_center_time)),
            )

    def _queue_formant_request(self, request: _FormantRequest, *, priority: tuple[int, float]) -> None:
        if request.cache_key == self._active_formant_request_key:
            return
        if request.cache_key in self._inflight_formant_requests:
            return
        existing = self._queued_formant_requests.get(request.cache_key)
        if existing is not None and existing[0] <= priority:
            return
        tile_start_time = request.window_start_time
        tile_end_time = request.window_end_time
        if self._find_cached_formant_tile(
            audio_revision=request.audio_revision,
            settings_key=request.settings_key,
            tile_start_time=tile_start_time,
            tile_end_time=tile_end_time,
        ) is not None:
            return
        self._queued_formant_requests[request.cache_key] = (priority, request)

    def _schedule_idle_formant_prefetch(self) -> None:
        if self._formant_idle_prefetch_timer is None:
            from PyQt6.QtCore import QTimer

            self._formant_idle_prefetch_timer = QTimer(self)
            self._formant_idle_prefetch_timer.setSingleShot(True)
            self._formant_idle_prefetch_timer.timeout.connect(self._prefetch_formants_when_idle)
        self._formant_idle_prefetch_timer.start(FORMANT_IDLE_PREFETCH_DELAY_MS)

    def _prefetch_formants_when_idle(self) -> None:
        waveform_data = self.waveform_cache.current_waveform
        if waveform_data is None or not self.spectrogram_settings.show_formants:
            return
        if self._current_formant_window is None:
            return
        settings_key = self._current_formant_settings_key()
        window_start_time, window_end_time = self._current_formant_window
        window_center_time = 0.5 * (window_start_time + window_end_time)
        visible_tile_keys = {
            (
                self._current_audio_revision,
                settings_key,
                int(round(tile_start_time * 1_000_000.0)),
                int(round(tile_end_time * 1_000_000.0)),
            )
            for tile_start_time, tile_end_time in self._tile_bounds_for_window(window_start_time, window_end_time)
        }
        for tile_start_time, tile_end_time in sorted(
            self._tile_bounds_for_window(0.0, waveform_data.duration_seconds),
            key=lambda bounds: abs((0.5 * (bounds[0] + bounds[1])) - window_center_time),
        ):
            request = self._build_formant_request(
                waveform_data=waveform_data,
                settings_key=settings_key,
                window_start_time=tile_start_time,
                window_end_time=tile_end_time,
            )
            if request.cache_key in visible_tile_keys:
                continue
            tile_center_time = 0.5 * (tile_start_time + tile_end_time)
            self._queue_formant_request(
                request,
                priority=(1, abs(tile_center_time - window_center_time)),
            )
        self._drain_formant_request_queue()

    def _drain_formant_request_queue(self) -> None:
        if self._active_formant_request_key is not None:
            return
        if not self._queued_formant_requests:
            return
        next_key = min(self._queued_formant_requests, key=lambda key: self._queued_formant_requests[key][0])
        _priority, request = self._queued_formant_requests.pop(next_key)
        self._submit_formant_request(request)

    def _submit_formant_request(self, request: _FormantRequest) -> None:
        self._inflight_formant_requests[request.cache_key] = request
        self._active_formant_request_key = request.cache_key
        future = self._get_formant_executor().submit(_compute_formants_for_request_isolated, request)
        future.add_done_callback(self._handle_formant_future_done)

    def _get_formant_executor(self) -> ThreadPoolExecutor:
        if self._formant_executor is not None:
            return self._formant_executor
        self._formant_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="movak-formants")
        return self._formant_executor

    def _handle_formant_future_done(self, future: Future) -> None:
        try:
            result = future.result()
        except Exception as error:
            result = _FormantResult(
                request=_FormantRequest(
                    audio_revision=self._current_audio_revision,
                    settings_key=self._current_formant_settings_key(),
                    window_start_time=0.0,
                    window_end_time=0.0,
                    sample_rate=1,
                    sample_offset_seconds=0.0,
                    samples=np.zeros(0, dtype=np.float32),
                ),
                error_message=str(error),
            )
        self.formant_analysis_completed.emit(result)

    def _handle_formant_analysis_completed(self, result: _FormantResult) -> None:
        self._inflight_formant_requests.pop(result.request.cache_key, None)
        if self._active_formant_request_key == result.request.cache_key:
            self._active_formant_request_key = None
        if result.request.audio_revision != self._current_audio_revision:
            self._drain_formant_request_queue()
            return

        if result.error_message is not None:
            cached_tile = _CachedFormantTile(
                audio_revision=result.request.audio_revision,
                settings_key=result.request.settings_key,
                tile_start_time=result.request.window_start_time,
                tile_end_time=result.request.window_end_time,
                times_seconds=np.zeros(0, dtype=np.float32),
                frequencies_hz=np.zeros((int(result.request.settings_key[1]), 0), dtype=np.float32),
                frame_confidence=np.zeros(0, dtype=np.float32),
            )
            self._formant_cache[result.request.cache_key] = cached_tile
            self._show_status_message(result.error_message)
        elif result.times_seconds is not None and result.frequencies_hz is not None:
            cached_tile = _CachedFormantTile(
                audio_revision=result.request.audio_revision,
                settings_key=result.request.settings_key,
                tile_start_time=result.request.window_start_time,
                tile_end_time=result.request.window_end_time,
                times_seconds=result.times_seconds,
                frequencies_hz=result.frequencies_hz,
                frame_confidence=(
                    result.frame_confidence
                    if result.frame_confidence is not None
                    else np.ones(result.times_seconds.shape, dtype=np.float32)
                ),
            )
            self._formant_cache[result.request.cache_key] = cached_tile
        else:
            return

        if self._current_formant_window is None:
            self._drain_formant_request_queue()
            return
        current_settings_key = self._current_formant_settings_key()
        if result.request.settings_key != current_settings_key:
            self._drain_formant_request_queue()
            return
        current_start_time, current_end_time = self._current_formant_window
        self._update_formants_from_cache(
            audio_revision=self._current_audio_revision,
            settings_key=current_settings_key,
            window_start_time=current_start_time,
            window_end_time=current_end_time,
        )
        self._drain_formant_request_queue()

    def _invalidate_formant_cache(self) -> None:
        self._current_audio_revision += 1
        self._formant_cache.clear()
        self._inflight_formant_requests.clear()
        self._queued_formant_requests.clear()
        self._active_formant_request_key = None
        self._current_formant_window = None
        if self._formant_idle_prefetch_timer is not None:
            self._formant_idle_prefetch_timer.stop()

    def _shutdown_formant_executor(self) -> None:
        if self._formant_executor is None:
            return
        self._formant_executor.shutdown(wait=False, cancel_futures=True)
        self._formant_executor = None

    def _show_status_message(self, message: str) -> None:
        if self.status_message_sink is None:
            return
        self.status_message_sink(message, STATUS_MESSAGE_TIMEOUT_MS)
