from __future__ import annotations

from typing import Protocol

from ...audio.waveform_cache import WaveformCache, WaveformData
from ...features.analysis_inspector import (
    ANALYSIS_WINDOW_DURATION_S,
    AnalysisSnapshot,
    build_analysis_snapshot,
    estimate_representative_formant_summary,
    extract_analysis_window_from_samples,
)
from ..components.transport_bar import STEREO_MODE

CURSOR_SAMPLE_TOLERANCE = 1


class CursorSource(Protocol):
    """Cursor-driven timeline surface needed by the analysis inspector."""

    cursor_time_changed: object
    cursor_time: float


class AnalysisInspectorView(Protocol):
    """View surface updated by the analysis inspector controller."""

    def set_analysis_snapshot(self, snapshot: AnalysisSnapshot) -> None: ...

    def show_placeholder_state(self, message: str) -> None: ...


class WaveformModeSource(Protocol):
    """UI surface exposing the active waveform display mode."""

    waveform_display_mode_requested: object

    def current_waveform_display_mode(self) -> str: ...


class AnalysisInspectorController:
    """Keep the right-panel analysis plots synchronized with the cursor."""

    def __init__(
        self,
        waveform_cache: WaveformCache,
        cursor_source: CursorSource,
        waveform_mode_source: WaveformModeSource,
        view: AnalysisInspectorView,
    ) -> None:
        self.waveform_cache = waveform_cache
        self.cursor_source = cursor_source
        self.waveform_mode_source = waveform_mode_source
        self.view = view
        self._last_signature: tuple[int, int, str] | None = None

        self.cursor_source.cursor_time_changed.connect(self.refresh)
        self.waveform_mode_source.waveform_display_mode_requested.connect(self.refresh)
        self.refresh(self.cursor_source.cursor_time)

    def refresh(self, cursor_time_s: float | None) -> None:
        """Recompute the analysis snapshot for the current cursor."""

        waveform_data = self.waveform_cache.current_waveform
        if waveform_data is None or waveform_data.sample_count == 0:
            self._last_signature = None
            self.view.show_placeholder_state("Load audio to inspect formants and PSD around the cursor.")
            return

        if cursor_time_s is None:
            self._last_signature = None
            self.view.show_placeholder_state("Move the cursor to inspect a short analysis slice.")
            return

        signature = self._build_signature(waveform_data, float(cursor_time_s))
        if signature == self._last_signature:
            return

        self._last_signature = signature
        snapshot = build_analysis_snapshot(
            waveform_data,
            float(cursor_time_s),
            analysis_window_duration_s=ANALYSIS_WINDOW_DURATION_S,
        )
        if snapshot.window is None:
            self.view.show_placeholder_state("Not enough nearby audio to analyze around the current cursor.")
            return
        snapshot = self._augment_snapshot_for_waveform_mode(snapshot, waveform_data, float(cursor_time_s))
        self.view.set_analysis_snapshot(snapshot)

    def _build_signature(self, waveform_data: WaveformData, cursor_time_s: float) -> tuple[int, int, str]:
        sample_rate = max(1, int(waveform_data.sample_rate))
        cursor_sample = int(round(cursor_time_s * sample_rate))
        if self._last_signature is not None and abs(cursor_sample - self._last_signature[1]) <= CURSOR_SAMPLE_TOLERANCE:
            cursor_sample = self._last_signature[1]
        return (id(waveform_data), cursor_sample, self.waveform_mode_source.current_waveform_display_mode())

    def _augment_snapshot_for_waveform_mode(
        self,
        snapshot: AnalysisSnapshot,
        waveform_data: WaveformData,
        cursor_time_s: float,
    ) -> AnalysisSnapshot:
        if self.waveform_mode_source.current_waveform_display_mode() != STEREO_MODE:
            return snapshot
        if waveform_data.channel_samples is None or waveform_data.channel_samples.shape[1] < 2:
            return snapshot

        channel_formants: list = []
        channel_confidences: list = []
        for channel_index in range(2):
            analysis_window = extract_analysis_window_from_samples(
                waveform_data.channel_samples[:, channel_index],
                waveform_data.sample_rate,
                cursor_time_s,
                analysis_window_duration_s=ANALYSIS_WINDOW_DURATION_S,
            )
            if analysis_window is None:
                channel_formants.append(None)
                channel_confidences.append(None)
                continue
            summary = estimate_representative_formant_summary(
                analysis_window.samples,
                analysis_window.sample_rate,
            )
            channel_formants.append(summary.point)
            channel_confidences.append(summary.confidence)

        snapshot.channel_formants = tuple(channel_formants)
        snapshot.channel_formant_confidences = tuple(channel_confidences)
        return snapshot
