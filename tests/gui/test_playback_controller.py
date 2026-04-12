import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QApplication, QDialog

from movak.audio.spectrogram import SpectrogramSettings
from movak.audio.loader import LoadedAudioData
from movak.audio.waveform_cache import WaveformCache
from movak.gui.components.transport_bar import TransportBar
from movak.gui.controllers.playback_controller import PlaybackController, _compute_formants_for_request


class FakePlaybackService(QObject):
    source_changed = pyqtSignal(str)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    playback_state_changed = pyqtSignal(QMediaPlayer.PlaybackState)
    error_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.current_path = ""
        self.current_file_name = ""
        self.position_ms = 0
        self.duration_ms = 0
        self.playback_state = QMediaPlayer.PlaybackState.StoppedState
        self.toggle_calls = 0
        self.stop_calls = 0
        self.loaded_paths: list[str] = []
        self.seek_positions_ms: list[int] = []
        self.play_calls = 0
        self.loop_enabled = False
        self.loop_range_ms: tuple[int, int] | None = None
        self.playback_rate = 1.0

    def load_file(self, path: str) -> None:
        self.current_path = path
        self.current_file_name = path.rsplit("/", maxsplit=1)[-1]
        self.loaded_paths.append(path)

    def toggle_play_pause(self) -> None:
        self.toggle_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1

    def pause(self) -> None:
        return

    def play(self) -> None:
        self.play_calls += 1

    def set_position_ms(self, position_ms: int) -> None:
        self.seek_positions_ms.append(position_ms)

    def set_loop_enabled(self, enabled: bool) -> None:
        self.loop_enabled = enabled

    def set_loop_range_ms(self, start_ms: int, end_ms: int) -> None:
        self.loop_range_ms = (start_ms, end_ms)

    def clear_loop_range(self) -> None:
        self.loop_range_ms = None

    def set_playback_rate(self, playback_rate: float) -> None:
        self.playback_rate = playback_rate


class FakeWaveformView:
    def __init__(self) -> None:
        self.waveform_data = None
        self.clear_calls = 0
        self.display_mode = "mono"

    def set_waveform_data(self, waveform_data) -> None:
        self.waveform_data = waveform_data

    def clear_waveform(self) -> None:
        self.clear_calls += 1

    def set_display_mode(self, mode: str) -> None:
        self.display_mode = mode


class FakeSpectrogramView(QObject):
    settings_requested = pyqtSignal()
    point_selected = pyqtSignal(float, float)
    region_selected = pyqtSignal(float, float, float, float)

    def __init__(self) -> None:
        super().__init__()
        self.spectrogram = None
        self.duration = None
        self.frame_step_seconds = None
        self.frame_start_seconds = None
        self.frame_end_seconds = None
        self.formant_times_seconds = None
        self.formant_frequencies_hz = None
        self.formant_frame_confidence = None
        self.clear_calls = 0
        self.clear_formant_calls = 0

    def set_spectrogram_data(
        self,
        spectrogram,
        duration: float,
        max_frequency_hz: float | None = None,
        frame_step_seconds: float | None = None,
        frame_start_seconds: float | None = None,
        frame_end_seconds: float | None = None,
    ) -> None:
        self.spectrogram = spectrogram
        self.duration = duration
        self.frame_step_seconds = frame_step_seconds
        self.frame_start_seconds = frame_start_seconds
        self.frame_end_seconds = frame_end_seconds

    def set_formant_data(self, times_seconds, frequencies_hz, frame_confidence=None) -> None:
        self.formant_times_seconds = times_seconds
        self.formant_frequencies_hz = frequencies_hz
        self.formant_frame_confidence = frame_confidence

    def clear_formants(self) -> None:
        self.clear_formant_calls += 1
        self.formant_times_seconds = None
        self.formant_frequencies_hz = None
        self.formant_frame_confidence = None

    def clear_spectrogram(self) -> None:
        self.clear_calls += 1


class FakeTimelineViewport(QObject):
    time_selected = pyqtSignal(float)
    visible_range_changed = pyqtSignal(float, float)

    def __init__(self) -> None:
        super().__init__()
        self.total_duration = None
        self.cursor_time = None
        self.visible_start_time = 0.0
        self.visible_end_time = 6.0

    def set_total_duration(self, total_duration: float) -> None:
        self.total_duration = total_duration

    def set_cursor_time(self, cursor_time: float) -> None:
        self.cursor_time = cursor_time

    def set_visible_time_range(self, start_time: float, end_time: float) -> None:
        self.visible_start_time = start_time
        self.visible_end_time = end_time
        self.visible_range_changed.emit(start_time, end_time)


class FakeSpectrogramSettingsDialog(QDialog):
    def __init__(self, settings: SpectrogramSettings, response_settings: SpectrogramSettings) -> None:
        super().__init__()
        self.initial_settings = settings
        self._response_settings = response_settings

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def settings(self) -> SpectrogramSettings:
        return self._response_settings


def _run_formant_request_immediately(controller, request) -> None:
    controller._handle_formant_analysis_completed(_compute_formants_for_request(request))


def test_playback_controller_updates_transport_bar_from_service_signals():
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    transport_bar.show()
    app.processEvents()

    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    status_messages: list[str] = []
    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
        status_message_sink=lambda message, _timeout: status_messages.append(message),
    )

    assert controller is not None
    assert transport_bar.source_label.text() == "No audio loaded"
    assert transport_bar.position_label.text() == "00:00"
    assert transport_bar.duration_label.text() == "00:00"
    assert transport_bar.play_button.text() == "Play"
    assert transport_bar.waveform_mode_combo.isEnabled() is False
    assert playback_service.loop_enabled is False
    assert playback_service.playback_rate == 1.0

    playback_service.current_path = "/tmp/example.wav"
    playback_service.current_file_name = "example.wav"
    playback_service.source_changed.emit("example.wav")
    playback_service.position_changed.emit(65_000)
    playback_service.duration_changed.emit(125_000)
    playback_service.playback_state_changed.emit(QMediaPlayer.PlaybackState.PlayingState)
    app.processEvents()

    assert transport_bar.source_label.text() == "example.wav"
    assert transport_bar.position_label.text() == "01:05"
    assert transport_bar.duration_label.text() == "02:05"
    assert transport_bar.play_button.text() == "Pause"
    assert timeline_viewport.cursor_time == 65.0

    transport_bar.play_pause_requested.emit()
    transport_bar.stop_requested.emit()

    assert playback_service.toggle_calls == 1
    assert playback_service.stop_calls == 1

    playback_service.error_changed.emit("Test error")
    app.processEvents()
    assert status_messages[-1] == "Test error"

    transport_bar.close()


def test_playback_controller_updates_playback_rate_from_transport_bar():
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )

    rate_index = transport_bar.rate_combo.findData(1.5)
    transport_bar.rate_combo.setCurrentIndex(rate_index)
    app.processEvents()

    assert playback_service.playback_rate == 1.5
    assert controller is not None

    transport_bar.close()


def test_playback_controller_loops_selected_region_when_loop_is_enabled():
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    playback_service.current_path = "/tmp/example.wav"
    playback_service.position_ms = 2_400
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )

    spectrogram_view.region_selected.emit(0.5, 1.5, 300.0, 1_800.0)
    transport_bar.loop_button.setChecked(True)
    transport_bar.play_pause_requested.emit()
    app.processEvents()

    assert playback_service.loop_enabled is True
    assert playback_service.loop_range_ms == (500, 1_500)
    assert playback_service.toggle_calls == 1
    assert controller is not None

    transport_bar.close()


def test_playback_controller_clears_loop_range_when_point_is_selected():
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )

    spectrogram_view.region_selected.emit(0.5, 1.5, 300.0, 1_800.0)
    assert playback_service.loop_range_ms == (500, 1_500)

    spectrogram_view.point_selected.emit(0.75, 900.0)
    app.processEvents()

    assert playback_service.loop_range_ms is None
    assert controller is not None

    transport_bar.close()


def test_playback_controller_loads_waveform_and_updates_timeline(monkeypatch):
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    status_messages: list[str] = []
    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
        file_picker=lambda *_args: ("/tmp/example.wav", "Audio Files"),
        status_message_sink=lambda message, _timeout: status_messages.append(message),
    )

    monkeypatch.setattr(
        "movak.gui.controllers.playback_controller.load_audio_for_waveform",
        lambda _path: LoadedAudioData(
            samples=np.array([0.0, 0.5, -0.5], dtype=np.float32),
            sample_rate=4,
            duration_seconds=0.75,
            channel_samples=np.column_stack(
                (
                    np.array([0.0, 0.5, -0.5], dtype=np.float32),
                    np.array([0.25, 0.0, -0.25], dtype=np.float32),
                )
            ).astype(np.float32),
            channel_count=2,
        ),
    )
    monkeypatch.setattr(
        "movak.gui.controllers.playback_controller.normalize_local_audio_path",
        lambda path: path,
    )

    controller.open_audio_file()
    app.processEvents()

    assert playback_service.loaded_paths == ["/tmp/example.wav"]
    assert waveform_view.waveform_data is not None
    assert waveform_view.waveform_data.sample_count == 3
    assert spectrogram_view.spectrogram is not None
    assert spectrogram_view.duration == 0.75
    assert transport_bar.waveform_mode_combo.isEnabled() is True
    assert waveform_view.display_mode == "mono"
    stereo_index = transport_bar.waveform_mode_combo.findData("stereo")
    transport_bar.waveform_mode_combo.setCurrentIndex(stereo_index)
    app.processEvents()
    assert waveform_view.display_mode == "stereo"
    assert timeline_viewport.total_duration == 0.75
    assert timeline_viewport.cursor_time == 0.0
    assert status_messages[-1] == "Loaded audio: example.wav"


def test_playback_controller_seeks_when_timeline_time_is_clicked():
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )

    assert controller is not None

    playback_service.current_path = "/tmp/example.wav"
    timeline_viewport.time_selected.emit(3.25)
    app.processEvents()

    assert timeline_viewport.cursor_time == 3.25
    assert playback_service.seek_positions_ms == [3250]


def test_playback_controller_rebuilds_spectrogram_from_settings_dialog(monkeypatch):
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()

    requested_settings = SpectrogramSettings(
        window_length_s=0.008,
        time_step_s=0.003,
        max_frequency_hz=4_200.0,
        dynamic_range_db=60.0,
        preemphasis_from_hz=75.0,
    )
    captured_settings: list[SpectrogramSettings] = []

    def fake_build_spectrogram(samples, sample_rate, *, settings=None, **_kwargs):
        assert settings is not None
        captured_settings.append(settings)

        class Result:
            magnitude = np.ones((8, 16), dtype=np.float32)
            duration_seconds = len(samples) / sample_rate
            frequency_hz = np.linspace(0.0, settings.max_frequency_hz, num=8, dtype=np.float32)
            frame_step_seconds = settings.time_step_s
            frame_start_seconds = 0.0
            frame_end_seconds = duration_seconds

        duration_seconds = len(samples) / sample_rate
        Result.duration_seconds = duration_seconds
        Result.frame_end_seconds = duration_seconds
        return Result()

    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_spectrogram", fake_build_spectrogram)

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
        spectrogram_settings_dialog_factory=lambda settings, _parent: FakeSpectrogramSettingsDialog(
            settings,
            requested_settings,
        ),
    )
    controller.waveform_cache.set_waveform(
        LoadedAudioData(
            samples=np.array([0.0, 0.5, -0.5, 0.25], dtype=np.float32),
            sample_rate=4,
            duration_seconds=1.0,
        )
    )

    spectrogram_view.settings_requested.emit()
    app.processEvents()

    assert captured_settings[-1] == requested_settings
    assert spectrogram_view.spectrogram is not None
    assert spectrogram_view.frame_step_seconds == requested_settings.time_step_s


def test_playback_controller_rebuilds_formants_when_enabled(monkeypatch):
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()

    requested_settings = SpectrogramSettings(
        show_formants=True,
        max_number_of_formants=4,
        formant_max_frequency_hz=4_800.0,
        formant_window_length_s=0.030,
        formant_preemphasis_from_hz=75.0,
    )
    captured_formant_settings = []

    def fake_build_spectrogram(samples, sample_rate, *, settings=None, **_kwargs):
        class Result:
            magnitude = np.ones((8, 16), dtype=np.float32)
            duration_seconds = len(samples) / sample_rate
            frequency_hz = np.linspace(0.0, 5_000.0, num=8, dtype=np.float32)
            frame_step_seconds = settings.time_step_s
            frame_start_seconds = 0.0
            frame_end_seconds = len(samples) / sample_rate

        return Result()

    def fake_build_formant_tracks(samples, sample_rate, *, settings=None):
        captured_formant_settings.append(settings)

        class Result:
            times_seconds = np.array([0.1, 0.2, 0.3], dtype=np.float32)
            frequencies_hz = np.array(
                [
                    [500.0, 520.0, 540.0],
                    [1_500.0, 1_520.0, 1_540.0],
                    [2_500.0, 2_520.0, 2_540.0],
                    [3_500.0, 3_520.0, 3_540.0],
                ],
                dtype=np.float32,
            )
            frame_confidence = np.array([0.9, 0.6, 0.3], dtype=np.float32)

        return Result()

    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_spectrogram", fake_build_spectrogram)
    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_formant_tracks", fake_build_formant_tracks)

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
        spectrogram_settings_dialog_factory=lambda settings, _parent: FakeSpectrogramSettingsDialog(
            settings,
            requested_settings,
        ),
    )
    monkeypatch.setattr(controller, "_submit_formant_request", lambda request: _run_formant_request_immediately(controller, request))
    controller.waveform_cache.set_waveform(
        LoadedAudioData(
            samples=np.array([0.0, 0.5, -0.5, 0.25], dtype=np.float32),
            sample_rate=4,
            duration_seconds=1.0,
        )
    )

    spectrogram_view.settings_requested.emit()
    app.processEvents()

    assert captured_formant_settings
    assert captured_formant_settings[-1].time_step_s == requested_settings.time_step_s
    assert captured_formant_settings[-1].max_number_of_formants == requested_settings.max_number_of_formants
    assert captured_formant_settings[-1].max_frequency_hz == requested_settings.formant_max_frequency_hz
    assert spectrogram_view.formant_times_seconds is not None
    assert spectrogram_view.formant_frequencies_hz.shape == (4, 3)
    assert np.allclose(spectrogram_view.formant_frame_confidence, np.array([0.9, 0.6, 0.3], dtype=np.float32))


def test_playback_controller_builds_formants_for_buffered_visible_window(monkeypatch):
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    timeline_viewport.set_visible_time_range(1.0, 3.0)

    def fake_build_spectrogram(samples, sample_rate, *, settings=None, **_kwargs):
        class Result:
            magnitude = np.ones((8, 16), dtype=np.float32)
            duration_seconds = len(samples) / sample_rate
            frequency_hz = np.linspace(0.0, 5_000.0, num=8, dtype=np.float32)
            frame_step_seconds = settings.time_step_s
            frame_start_seconds = 0.0
            frame_end_seconds = len(samples) / sample_rate

        return Result()

    captured_sample_lengths = []

    def fake_build_formant_tracks(samples, sample_rate, *, settings=None):
        captured_sample_lengths.append(len(samples))
        class Result:
            times_seconds = np.array([0.0, 0.25, 0.5], dtype=np.float32)
            frequencies_hz = np.array([[500.0, 520.0, 540.0]], dtype=np.float32)
            frame_confidence = np.array([0.8, 0.5, 0.2], dtype=np.float32)

        return Result()

    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_spectrogram", fake_build_spectrogram)
    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_formant_tracks", fake_build_formant_tracks)

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )
    monkeypatch.setattr(controller, "_submit_formant_request", lambda request: _run_formant_request_immediately(controller, request))
    controller.spectrogram_settings = SpectrogramSettings(show_formants=True)
    controller.waveform_cache.set_waveform(
        LoadedAudioData(
            samples=np.arange(1_000, dtype=np.float32),
            sample_rate=100,
            duration_seconds=10.0,
        )
    )

    controller._refresh_formants()
    app.processEvents()

    assert captured_sample_lengths == [100, 100, 100, 100]
    assert np.allclose(
        spectrogram_view.formant_times_seconds,
        np.array([0.5, 1.0, 1.25, 1.5, 2.0, 2.25, 2.5, 3.0, 3.25, 3.5], dtype=np.float32),
    )
    assert np.allclose(
        spectrogram_view.formant_frame_confidence,
        np.array([0.2, 0.8, 0.5, 0.2, 0.8, 0.5, 0.2, 0.8, 0.5, 0.2], dtype=np.float32),
    )


def test_playback_controller_reuses_cached_formants_within_buffer(monkeypatch):
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    timeline_viewport.set_visible_time_range(1.0, 3.0)

    def fake_build_spectrogram(samples, sample_rate, *, settings=None, **_kwargs):
        class Result:
            magnitude = np.ones((8, 16), dtype=np.float32)
            duration_seconds = len(samples) / sample_rate
            frequency_hz = np.linspace(0.0, 5_000.0, num=8, dtype=np.float32)
            frame_step_seconds = settings.time_step_s
            frame_start_seconds = 0.0
            frame_end_seconds = len(samples) / sample_rate

        return Result()

    build_calls = []

    def fake_build_formant_tracks(samples, sample_rate, *, settings=None):
        build_calls.append(len(samples))
        class Result:
            times_seconds = np.array([0.0, 0.1], dtype=np.float32)
            frequencies_hz = np.array([[500.0, 520.0]], dtype=np.float32)
            frame_confidence = np.array([0.7, 0.4], dtype=np.float32)

        return Result()

    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_spectrogram", fake_build_spectrogram)
    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_formant_tracks", fake_build_formant_tracks)

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )
    monkeypatch.setattr(controller, "_submit_formant_request", lambda request: _run_formant_request_immediately(controller, request))
    controller.spectrogram_settings = SpectrogramSettings(show_formants=True)
    controller.waveform_cache.set_waveform(
        LoadedAudioData(
            samples=np.arange(1_000, dtype=np.float32),
            sample_rate=100,
            duration_seconds=10.0,
        )
    )

    controller._refresh_formants()
    timeline_viewport.set_visible_time_range(1.1, 2.9)
    app.processEvents()

    assert build_calls == [100, 100, 100, 100]


def test_playback_controller_reuses_cached_tiles_after_viewport_change(monkeypatch):
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    timeline_viewport.set_visible_time_range(1.0, 3.0)

    build_calls = []

    def fake_build_formant_tracks(samples, sample_rate, *, settings=None):
        build_calls.append(len(samples))
        class Result:
            times_seconds = np.array([0.0, 0.25, 0.5], dtype=np.float32)
            frequencies_hz = np.array([[500.0, 520.0, 540.0]], dtype=np.float32)
            frame_confidence = np.array([0.8, 0.5, 0.2], dtype=np.float32)

        return Result()

    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_formant_tracks", fake_build_formant_tracks)

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )
    monkeypatch.setattr(controller, "_submit_formant_request", lambda request: _run_formant_request_immediately(controller, request))
    controller.spectrogram_settings = SpectrogramSettings(show_formants=True)
    controller.waveform_cache.set_waveform(
        LoadedAudioData(
            samples=np.arange(1_000, dtype=np.float32),
            sample_rate=100,
            duration_seconds=10.0,
        )
    )

    controller._refresh_formants()
    timeline_viewport.set_visible_time_range(1.2, 2.2)
    app.processEvents()

    assert build_calls == [100, 100, 100, 100]


def test_playback_controller_reuses_cached_formants_after_leaving_and_returning(monkeypatch):
    app = QApplication.instance() or QApplication([])
    transport_bar = TransportBar()
    playback_service = FakePlaybackService()
    waveform_view = FakeWaveformView()
    spectrogram_view = FakeSpectrogramView()
    timeline_viewport = FakeTimelineViewport()
    timeline_viewport.set_visible_time_range(1.0, 3.0)

    build_calls = []

    def fake_build_formant_tracks(samples, sample_rate, *, settings=None):
        build_calls.append(len(samples))
        class Result:
            times_seconds = np.array([0.0, 0.25, 0.5], dtype=np.float32)
            frequencies_hz = np.array([[500.0, 520.0, 540.0]], dtype=np.float32)
            frame_confidence = np.full(3, 0.8, dtype=np.float32)

        return Result()

    monkeypatch.setattr("movak.gui.controllers.playback_controller.build_formant_tracks", fake_build_formant_tracks)

    controller = PlaybackController(
        playback_service,
        transport_bar,
        WaveformCache(),
        waveform_view,
        spectrogram_view,
        timeline_viewport,
    )
    monkeypatch.setattr(controller, "_submit_formant_request", lambda request: _run_formant_request_immediately(controller, request))
    controller.spectrogram_settings = SpectrogramSettings(show_formants=True)
    controller.waveform_cache.set_waveform(
        LoadedAudioData(
            samples=np.arange(1_000, dtype=np.float32),
            sample_rate=100,
            duration_seconds=10.0,
        )
    )

    controller._refresh_formants()
    first_times = np.array(spectrogram_view.formant_times_seconds, copy=True)
    timeline_viewport.set_visible_time_range(5.0, 7.0)
    app.processEvents()
    timeline_viewport.set_visible_time_range(1.0, 3.0)
    app.processEvents()

    assert build_calls == [100, 100, 100, 100, 100, 100, 100, 100]
    assert np.allclose(spectrogram_view.formant_times_seconds, first_times)
