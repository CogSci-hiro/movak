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
from movak.gui.controllers.playback_controller import PlaybackController


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
        return

    def set_position_ms(self, position_ms: int) -> None:
        self.seek_positions_ms.append(position_ms)


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

    def __init__(self) -> None:
        super().__init__()
        self.spectrogram = None
        self.duration = None
        self.frame_step_seconds = None
        self.frame_start_seconds = None
        self.frame_end_seconds = None
        self.clear_calls = 0

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

    def clear_spectrogram(self) -> None:
        self.clear_calls += 1


class FakeTimelineViewport(QObject):
    time_selected = pyqtSignal(float)

    def __init__(self) -> None:
        super().__init__()
        self.total_duration = None
        self.cursor_time = None

    def set_total_duration(self, total_duration: float) -> None:
        self.total_duration = total_duration

    def set_cursor_time(self, cursor_time: float) -> None:
        self.cursor_time = cursor_time


class FakeSpectrogramSettingsDialog(QDialog):
    def __init__(self, settings: SpectrogramSettings, response_settings: SpectrogramSettings) -> None:
        super().__init__()
        self.initial_settings = settings
        self._response_settings = response_settings

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def settings(self) -> SpectrogramSettings:
        return self._response_settings


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
