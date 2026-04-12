import numpy as np

from movak.audio.waveform_cache import WaveformCache, WaveformData
from movak.features.analysis_inspector import AnalysisSnapshot, AnalysisWindow, FormantPoint, FormantSummary
from movak.gui.components.transport_bar import MONO_MODE, STEREO_MODE
from movak.gui.controllers.analysis_inspector_controller import AnalysisInspectorController


class _Signal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args) -> None:
        for callback in self._callbacks:
            callback(*args)


class _CursorSource:
    def __init__(self, cursor_time: float) -> None:
        self.cursor_time_changed = _Signal()
        self.cursor_time = cursor_time


class _WaveformModeSource:
    def __init__(self, mode: str) -> None:
        self.waveform_display_mode_requested = _Signal()
        self._mode = mode

    def current_waveform_display_mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.waveform_display_mode_requested.emit(mode)


class _View:
    def __init__(self) -> None:
        self.snapshot = None
        self.placeholder_message = None

    def set_analysis_snapshot(self, snapshot) -> None:
        self.snapshot = snapshot

    def show_placeholder_state(self, message: str) -> None:
        self.placeholder_message = message


def test_analysis_inspector_controller_adds_per_channel_formants_in_stereo(monkeypatch):
    waveform_cache = WaveformCache()
    waveform_cache._current_waveform = WaveformData(
        samples=np.array([0.15, 0.25, 0.35, 0.45], dtype=np.float32),
        sample_rate=1_000,
        duration_seconds=0.004,
        channel_samples=np.column_stack(
            (
                np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
                np.array([0.5, 0.6, 0.7, 0.8], dtype=np.float32),
            )
        ),
        channel_count=2,
    )
    cursor_source = _CursorSource(0.002)
    waveform_mode_source = _WaveformModeSource(STEREO_MODE)
    view = _View()

    monkeypatch.setattr(
        "movak.gui.controllers.analysis_inspector_controller.build_analysis_snapshot",
        lambda *_args, **_kwargs: AnalysisSnapshot(
            window=AnalysisWindow(
                cursor_time_s=0.002,
                start_time_s=0.0,
                end_time_s=0.004,
                sample_rate=1_000,
                samples=np.array([0.15, 0.25, 0.35, 0.45], dtype=np.float32),
            ),
            psd=None,
            formant=FormantPoint(f1_hz=500.0, f2_hz=1_500.0),
            formant_frequencies_hz=np.array([500.0, 1_500.0], dtype=np.float32),
            formant_confidence=0.8,
        ),
    )
    monkeypatch.setattr(
        "movak.gui.controllers.analysis_inspector_controller.extract_analysis_window_from_samples",
        lambda samples, sample_rate, cursor_time_s, **_kwargs: AnalysisWindow(
            cursor_time_s=float(cursor_time_s),
            start_time_s=0.0,
            end_time_s=float(np.asarray(samples).size) / float(sample_rate),
            sample_rate=sample_rate,
            samples=np.asarray(samples, dtype=np.float32),
        ),
    )
    monkeypatch.setattr(
        "movak.gui.controllers.analysis_inspector_controller.estimate_representative_formant_summary",
        lambda samples, *_args, **_kwargs: FormantSummary(
            point=FormantPoint(f1_hz=float(np.mean(samples) * 1_000.0), f2_hz=float(np.mean(samples) * 2_000.0)),
            frequencies_hz=np.zeros(0, dtype=np.float32),
            confidence=float(np.mean(samples)),
        ),
    )

    controller = AnalysisInspectorController(
        waveform_cache,
        cursor_source,
        waveform_mode_source,
        view,
    )

    assert view.snapshot is not None
    assert view.snapshot.channel_formants == (
        FormantPoint(f1_hz=250.0, f2_hz=500.0),
        FormantPoint(f1_hz=650.0, f2_hz=1_300.0),
    )
    assert view.snapshot.channel_formant_confidences == (0.25, 0.6499999761581421)


def test_analysis_inspector_controller_keeps_mono_snapshot_when_waveform_mode_is_mono(monkeypatch):
    waveform_cache = WaveformCache()
    waveform_cache._current_waveform = WaveformData(
        samples=np.array([0.15, 0.25, 0.35, 0.45], dtype=np.float32),
        sample_rate=1_000,
        duration_seconds=0.004,
        channel_samples=np.column_stack(
            (
                np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
                np.array([0.5, 0.6, 0.7, 0.8], dtype=np.float32),
            )
        ),
        channel_count=2,
    )
    cursor_source = _CursorSource(0.002)
    waveform_mode_source = _WaveformModeSource(MONO_MODE)
    view = _View()

    monkeypatch.setattr(
        "movak.gui.controllers.analysis_inspector_controller.build_analysis_snapshot",
        lambda *_args, **_kwargs: AnalysisSnapshot(
            window=AnalysisWindow(
                cursor_time_s=0.002,
                start_time_s=0.0,
                end_time_s=0.004,
                sample_rate=1_000,
                samples=np.array([0.15, 0.25, 0.35, 0.45], dtype=np.float32),
            ),
            psd=None,
            formant=FormantPoint(f1_hz=500.0, f2_hz=1_500.0),
            formant_frequencies_hz=np.array([500.0, 1_500.0], dtype=np.float32),
            formant_confidence=0.8,
        ),
    )

    controller = AnalysisInspectorController(
        waveform_cache,
        cursor_source,
        waveform_mode_source,
        view,
    )

    assert controller is not None
    assert view.snapshot is not None
    assert view.snapshot.channel_formants == ()
    assert view.snapshot.channel_formant_confidences == ()
