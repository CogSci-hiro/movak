"""Helpers for cursor-centered audio inspection in the right panel."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..audio.waveform_cache import WaveformData
from .formants import FormantSettings, build_formant_tracks

ANALYSIS_WINDOW_DURATION_S = 0.2
ANALYSIS_MIN_SAMPLE_COUNT = 128
PSD_MAX_FREQUENCY_HZ = 5_000.0
PSD_SEGMENT_DURATION_S = 0.025
PSD_OVERLAP_RATIO = 0.5
FORMANT_MIN_F1_HZ = 150.0
FORMANT_MAX_F1_HZ = 1_500.0
FORMANT_MIN_F2_HZ = 500.0
FORMANT_MAX_F2_HZ = 4_000.0
FORMANT_MIN_ALPHA = 24.0
FORMANT_MAX_ALPHA = 210.0
FORMANT_ALPHA_GAMMA = 1.8


@dataclass(slots=True)
class AnalysisWindow:
    """Cursor-centered audio excerpt used for right-panel analysis.

    Parameters
    ----------
    cursor_time_s
        Cursor time requested by the UI.
    start_time_s
        Inclusive analysis-window start in seconds.
    end_time_s
        Exclusive analysis-window end in seconds.
    sample_rate
        Sampling rate for ``samples`` in Hz.
    samples
        Mono waveform samples for the current analysis window.
    """

    cursor_time_s: float
    start_time_s: float
    end_time_s: float
    sample_rate: int
    samples: np.ndarray


@dataclass(slots=True)
class PowerSpectralDensityEstimate:
    """Power spectral density estimate for the current audio slice."""

    frequencies_hz: np.ndarray
    power_db: np.ndarray


@dataclass(slots=True)
class FormantPoint:
    """Representative F1/F2 estimate for the current audio slice."""

    f1_hz: float
    f2_hz: float


@dataclass(slots=True)
class FormantSummary:
    """Representative formant estimates for the current audio slice."""

    point: FormantPoint | None
    frequencies_hz: np.ndarray
    confidence: float | None


@dataclass(slots=True)
class AnalysisSnapshot:
    """Complete right-panel analysis payload for a single cursor position."""

    window: AnalysisWindow | None
    psd: PowerSpectralDensityEstimate | None
    formant: FormantPoint | None
    formant_frequencies_hz: np.ndarray
    formant_confidence: float | None
    channel_formants: tuple[FormantPoint | None, ...] = ()
    channel_formant_confidences: tuple[float | None, ...] = ()


def build_analysis_snapshot(
    waveform_data: WaveformData | None,
    cursor_time_s: float | None,
    *,
    analysis_window_duration_s: float = ANALYSIS_WINDOW_DURATION_S,
    psd_max_frequency_hz: float = PSD_MAX_FREQUENCY_HZ,
    formant_settings: FormantSettings | None = None,
) -> AnalysisSnapshot:
    """Build PSD and representative formants around the current cursor.

    Parameters
    ----------
    waveform_data
        Cached waveform backing the active audio file.
    cursor_time_s
        Cursor or playhead time in seconds.
    analysis_window_duration_s
        Target analysis-window duration in seconds.
    psd_max_frequency_hz
        Maximum plotted PSD frequency in Hz.
    formant_settings
        Optional Praat Burg formant settings.
    """

    analysis_window = extract_analysis_window(
        waveform_data,
        cursor_time_s,
        analysis_window_duration_s=analysis_window_duration_s,
    )
    if analysis_window is None:
        return AnalysisSnapshot(
            window=None,
            psd=None,
            formant=None,
            formant_frequencies_hz=np.zeros(0, dtype=np.float32),
            formant_confidence=None,
            channel_formants=(),
            channel_formant_confidences=(),
        )

    psd_estimate = compute_power_spectral_density(
        analysis_window.samples,
        analysis_window.sample_rate,
        max_frequency_hz=psd_max_frequency_hz,
    )
    formant_summary = estimate_representative_formant_summary(
        analysis_window.samples,
        analysis_window.sample_rate,
        settings=formant_settings,
    )
    return AnalysisSnapshot(
        window=analysis_window,
        psd=psd_estimate,
        formant=formant_summary.point,
        formant_frequencies_hz=formant_summary.frequencies_hz,
        formant_confidence=formant_summary.confidence,
        channel_formants=(),
        channel_formant_confidences=(),
    )


def extract_analysis_window(
    waveform_data: WaveformData | None,
    cursor_time_s: float | None,
    *,
    analysis_window_duration_s: float = ANALYSIS_WINDOW_DURATION_S,
) -> AnalysisWindow | None:
    """Extract a short window centered on the current cursor.

    Parameters
    ----------
    waveform_data
        Cached waveform backing the active audio file.
    cursor_time_s
        Cursor or playhead time in seconds.
    analysis_window_duration_s
        Target duration of the extracted analysis window.
    """

    if waveform_data is None:
        return None
    return extract_analysis_window_from_samples(
        waveform_data.samples,
        waveform_data.sample_rate,
        cursor_time_s,
        analysis_window_duration_s=analysis_window_duration_s,
    )


def extract_analysis_window_from_samples(
    samples: np.ndarray | None,
    sample_rate: int,
    cursor_time_s: float | None,
    *,
    analysis_window_duration_s: float = ANALYSIS_WINDOW_DURATION_S,
) -> AnalysisWindow | None:
    """Extract a short cursor-centered window from a raw mono sample array."""

    if samples is None or cursor_time_s is None:
        return None
    normalized_samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if sample_rate <= 0 or normalized_samples.size <= 0:
        return None

    sample_rate = int(sample_rate)
    total_sample_count = int(normalized_samples.size)
    target_sample_count = max(1, int(round(analysis_window_duration_s * sample_rate)))
    center_sample = int(round(float(cursor_time_s) * sample_rate))
    center_sample = min(max(center_sample, 0), max(0, total_sample_count - 1))

    start_sample = center_sample - (target_sample_count // 2)
    end_sample = start_sample + target_sample_count
    if start_sample < 0:
        end_sample = min(total_sample_count, end_sample - start_sample)
        start_sample = 0
    if end_sample > total_sample_count:
        start_sample = max(0, start_sample - (end_sample - total_sample_count))
        end_sample = total_sample_count

    if end_sample - start_sample < ANALYSIS_MIN_SAMPLE_COUNT:
        return None

    window_samples = normalized_samples[start_sample:end_sample]
    if window_samples.size < ANALYSIS_MIN_SAMPLE_COUNT:
        return None

    return AnalysisWindow(
        cursor_time_s=float(cursor_time_s),
        start_time_s=float(start_sample) / float(sample_rate),
        end_time_s=float(end_sample) / float(sample_rate),
        sample_rate=sample_rate,
        samples=window_samples,
    )


def compute_power_spectral_density(
    samples: np.ndarray,
    sample_rate: int,
    *,
    max_frequency_hz: float = PSD_MAX_FREQUENCY_HZ,
    segment_duration_s: float = PSD_SEGMENT_DURATION_S,
    overlap_ratio: float = PSD_OVERLAP_RATIO,
) -> PowerSpectralDensityEstimate | None:
    """Compute a lightweight Welch-style PSD estimate using NumPy only."""

    if sample_rate <= 0:
        return None

    mono_samples = np.asarray(samples, dtype=np.float64).reshape(-1)
    if mono_samples.size < ANALYSIS_MIN_SAMPLE_COUNT:
        return None

    mono_samples = mono_samples - float(np.mean(mono_samples))
    segment_sample_count = max(64, int(round(segment_duration_s * sample_rate)))
    segment_sample_count = min(segment_sample_count, mono_samples.size)
    if segment_sample_count < 32:
        return None

    hop_sample_count = max(1, int(round(segment_sample_count * (1.0 - overlap_ratio))))
    if mono_samples.size == segment_sample_count:
        segment_starts = [0]
    else:
        last_start = mono_samples.size - segment_sample_count
        segment_starts = list(range(0, last_start + 1, hop_sample_count))
        if segment_starts[-1] != last_start:
            segment_starts.append(last_start)

    window = np.hanning(segment_sample_count)
    window_energy = float(np.sum(window**2))
    if window_energy <= 0.0:
        return None

    accumulated_power = np.zeros((segment_sample_count // 2) + 1, dtype=np.float64)
    for start_sample in segment_starts:
        segment = mono_samples[start_sample : start_sample + segment_sample_count]
        if segment.size != segment_sample_count:
            continue
        spectrum = np.fft.rfft(segment * window)
        power_density = (np.abs(spectrum) ** 2) / (float(sample_rate) * window_energy)
        if segment_sample_count > 1:
            power_density[1:-1] *= 2.0
        accumulated_power += power_density

    accumulated_power /= float(len(segment_starts))
    frequencies_hz = np.fft.rfftfreq(segment_sample_count, d=1.0 / float(sample_rate))
    valid_mask = frequencies_hz <= max_frequency_hz
    if not np.any(valid_mask):
        return None

    clipped_power = np.maximum(accumulated_power[valid_mask], np.finfo(np.float64).tiny)
    return PowerSpectralDensityEstimate(
        frequencies_hz=frequencies_hz[valid_mask].astype(np.float32),
        power_db=(10.0 * np.log10(clipped_power)).astype(np.float32),
    )


def estimate_representative_formants(
    samples: np.ndarray,
    sample_rate: int,
    *,
    settings: FormantSettings | None = None,
) -> FormantPoint | None:
    """Estimate a representative F1/F2 pair for the current audio slice."""

    return estimate_representative_formant_summary(
        samples,
        sample_rate,
        settings=settings,
    ).point


def estimate_representative_formant_summary(
    samples: np.ndarray,
    sample_rate: int,
    *,
    settings: FormantSettings | None = None,
) -> FormantSummary:
    """Estimate representative formant markers for the current audio slice."""

    if sample_rate <= 0:
        return FormantSummary(point=None, frequencies_hz=np.zeros(0, dtype=np.float32), confidence=None)

    mono_samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if mono_samples.size < ANALYSIS_MIN_SAMPLE_COUNT:
        return FormantSummary(point=None, frequencies_hz=np.zeros(0, dtype=np.float32), confidence=None)

    try:
        tracks = build_formant_tracks(mono_samples, sample_rate, settings=settings)
    except RuntimeError:
        return FormantSummary(point=None, frequencies_hz=np.zeros(0, dtype=np.float32), confidence=None)
    except ValueError:
        return FormantSummary(point=None, frequencies_hz=np.zeros(0, dtype=np.float32), confidence=None)

    representative_frequencies_hz = _estimate_representative_formant_frequencies(
        tracks.frequencies_hz,
        tracks.frame_confidence,
    )
    representative_point, representative_confidence = _estimate_representative_f1_f2_point(
        tracks.frequencies_hz,
        tracks.frame_confidence,
    )
    return FormantSummary(
        point=representative_point,
        frequencies_hz=representative_frequencies_hz,
        confidence=representative_confidence,
    )


def _estimate_representative_formant_frequencies(
    frequencies_hz: np.ndarray,
    frame_confidence: np.ndarray | None,
) -> np.ndarray:
    if frequencies_hz.ndim != 2 or frequencies_hz.shape[1] == 0:
        return np.zeros(0, dtype=np.float32)

    normalized_weights = _formant_frame_weights(frame_confidence, frequencies_hz.shape[1])
    representative_values: list[float] = []
    for formant_values in frequencies_hz:
        valid_mask = np.isfinite(formant_values) & (formant_values > 0.0)
        if not np.any(valid_mask):
            continue
        representative_values.append(
            _weighted_average(
                formant_values[valid_mask],
                normalized_weights[valid_mask],
            )
        )

    if not representative_values:
        return np.zeros(0, dtype=np.float32)
    return np.asarray(representative_values, dtype=np.float32)


def _estimate_representative_f1_f2_point(
    frequencies_hz: np.ndarray,
    frame_confidence: np.ndarray | None,
) -> tuple[FormantPoint | None, float | None]:
    if frequencies_hz.shape[0] < 2 or frequencies_hz.shape[1] == 0:
        return None, None

    f1_values = frequencies_hz[0]
    f2_values = frequencies_hz[1]
    normalized_confidence = _normalized_frame_confidence(frame_confidence, frequencies_hz.shape[1])
    normalized_weights = _formant_frame_weights(frame_confidence, frequencies_hz.shape[1])
    valid_mask = (
        np.isfinite(f1_values)
        & np.isfinite(f2_values)
        & (f1_values >= FORMANT_MIN_F1_HZ)
        & (f1_values <= FORMANT_MAX_F1_HZ)
        & (f2_values >= FORMANT_MIN_F2_HZ)
        & (f2_values <= FORMANT_MAX_F2_HZ)
        & (f2_values > f1_values)
    )
    if not np.any(valid_mask):
        return None, None

    representative_f1 = _weighted_average(f1_values[valid_mask], normalized_weights[valid_mask])
    representative_f2 = _weighted_average(f2_values[valid_mask], normalized_weights[valid_mask])
    representative_confidence = _weighted_average(
        normalized_confidence[valid_mask],
        normalized_weights[valid_mask],
    )
    return FormantPoint(f1_hz=representative_f1, f2_hz=representative_f2), representative_confidence


def _normalized_frame_confidence(frame_confidence: np.ndarray | None, frame_count: int) -> np.ndarray:
    if frame_count <= 0:
        return np.zeros(0, dtype=np.float32)
    if frame_confidence is None:
        return np.ones(frame_count, dtype=np.float32)

    normalized_confidence = np.asarray(frame_confidence, dtype=np.float32).reshape(-1)
    if normalized_confidence.size != frame_count:
        return np.ones(frame_count, dtype=np.float32)
    return np.clip(normalized_confidence, 0.0, 1.0)


def _formant_frame_weights(frame_confidence: np.ndarray | None, frame_count: int) -> np.ndarray:
    if frame_count <= 0:
        return np.zeros(0, dtype=np.float32)
    return _alpha_weight_from_confidence(_normalized_frame_confidence(frame_confidence, frame_count))


def _alpha_weight_from_confidence(confidence: np.ndarray) -> np.ndarray:
    clamped_confidence = np.clip(np.asarray(confidence, dtype=np.float32), 0.0, 1.0)
    normalized_confidence = clamped_confidence**FORMANT_ALPHA_GAMMA
    return FORMANT_MIN_ALPHA + ((FORMANT_MAX_ALPHA - FORMANT_MIN_ALPHA) * normalized_confidence)


def _weighted_average(values: np.ndarray, weights: np.ndarray) -> float:
    normalized_values = np.asarray(values, dtype=np.float32)
    normalized_weights = np.asarray(weights, dtype=np.float32)
    total_weight = float(np.sum(normalized_weights))
    if total_weight <= 0.0:
        return float(np.mean(normalized_values))
    return float(np.sum(normalized_values * normalized_weights) / total_weight)
