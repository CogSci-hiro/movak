"""Spectrogram generation helpers for timeline rendering."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PRAAT_DEFAULT_WINDOW_LENGTH_S = 0.005
PRAAT_DEFAULT_TIME_STEP_S = 0.002
PRAAT_DEFAULT_MAX_FREQUENCY_HZ = 5_000.0
PRAAT_DEFAULT_DYNAMIC_RANGE_DB = 50.0
PRAAT_DEFAULT_PREEMPHASIS_FROM_HZ = 50.0
MIN_FRAME_SIZE = 64
MIN_DISPLAY_FFT_SIZE = 1_024
EPSILON = 1e-12


@dataclass(slots=True)
class SpectrogramSettings:
    """User-adjustable spectrogram analysis settings."""

    window_length_s: float = PRAAT_DEFAULT_WINDOW_LENGTH_S
    time_step_s: float = PRAAT_DEFAULT_TIME_STEP_S
    max_frequency_hz: float = PRAAT_DEFAULT_MAX_FREQUENCY_HZ
    dynamic_range_db: float = PRAAT_DEFAULT_DYNAMIC_RANGE_DB
    preemphasis_from_hz: float = PRAAT_DEFAULT_PREEMPHASIS_FROM_HZ


@dataclass(slots=True)
class SpectrogramData:
    """Spectrogram image data ready for display."""

    magnitude: np.ndarray
    duration_seconds: float
    frequency_hz: np.ndarray
    frame_step_seconds: float
    frame_start_seconds: float
    frame_end_seconds: float


def build_spectrogram(
    samples: np.ndarray,
    sample_rate: int,
    *,
    settings: SpectrogramSettings | None = None,
    window_length_s: float = PRAAT_DEFAULT_WINDOW_LENGTH_S,
    time_step_s: float = PRAAT_DEFAULT_TIME_STEP_S,
    max_frequency_hz: float = PRAAT_DEFAULT_MAX_FREQUENCY_HZ,
    dynamic_range_db: float = PRAAT_DEFAULT_DYNAMIC_RANGE_DB,
    preemphasis_from_hz: float = PRAAT_DEFAULT_PREEMPHASIS_FROM_HZ,
) -> SpectrogramData:
    """Build a normalized, Praat-like log-power spectrogram from mono samples."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive.")
    active_settings = settings or SpectrogramSettings(
        window_length_s=window_length_s,
        time_step_s=time_step_s,
        max_frequency_hz=max_frequency_hz,
        dynamic_range_db=dynamic_range_db,
        preemphasis_from_hz=preemphasis_from_hz,
    )

    mono_samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    duration_seconds = float(mono_samples.size) / float(sample_rate) if mono_samples.size > 0 else 0.0
    frame_size = max(MIN_FRAME_SIZE, int(round(active_settings.window_length_s * sample_rate)))
    n_fft = max(MIN_DISPLAY_FFT_SIZE, _next_power_of_two(frame_size))
    frequency_hz = np.fft.rfftfreq(n_fft, d=1.0 / float(sample_rate)).astype(np.float32)
    visible_frequency_hz = frequency_hz[frequency_hz <= active_settings.max_frequency_hz]
    hop = max(1, int(round(active_settings.time_step_s * sample_rate)))
    frame_step_seconds = hop / float(sample_rate)
    if mono_samples.size == 0:
        return SpectrogramData(
            magnitude=np.zeros((visible_frequency_hz.size, 1), dtype=np.float32),
            duration_seconds=duration_seconds,
            frequency_hz=visible_frequency_hz,
            frame_step_seconds=frame_step_seconds,
            frame_start_seconds=0.0,
            frame_end_seconds=frame_step_seconds,
        )

    emphasized_samples = _apply_preemphasis(mono_samples, sample_rate, active_settings.preemphasis_from_hz)
    padded_samples = _pad_for_centered_stft(emphasized_samples, frame_size=frame_size, hop=hop)
    frames, frame_center_times = _frame_signal(
        padded_samples,
        frame_size=frame_size,
        hop=hop,
        sample_rate=sample_rate,
        original_duration_seconds=duration_seconds,
    )
    if frames.size == 0:
        return SpectrogramData(
            magnitude=np.zeros((visible_frequency_hz.size, 1), dtype=np.float32),
            duration_seconds=duration_seconds,
            frequency_hz=visible_frequency_hz,
            frame_step_seconds=frame_step_seconds,
            frame_start_seconds=0.0,
            frame_end_seconds=frame_step_seconds,
        )

    window = _gaussian_window(frame_size)
    spectra = np.fft.rfft(frames * window, n=n_fft, axis=1)
    power = (np.abs(spectra, dtype=np.float64) ** 2.0).T
    frequency_mask = frequency_hz <= active_settings.max_frequency_hz
    visible_power = power[frequency_mask, :]
    magnitude = _normalize_log_power(visible_power, dynamic_range_db=active_settings.dynamic_range_db)
    frame_start_seconds = max(0.0, float(frame_center_times[0] - (0.5 * frame_step_seconds)))
    frame_end_seconds = min(
        max(duration_seconds, frame_step_seconds),
        float(frame_center_times[-1] + (0.5 * frame_step_seconds)),
    )
    return SpectrogramData(
        magnitude=magnitude,
        duration_seconds=duration_seconds,
        frequency_hz=visible_frequency_hz,
        frame_step_seconds=frame_step_seconds,
        frame_start_seconds=frame_start_seconds,
        frame_end_seconds=frame_end_seconds,
    )


def _next_power_of_two(value: int) -> int:
    bounded_value = max(1, value)
    return 1 << (bounded_value - 1).bit_length()


def _apply_preemphasis(samples: np.ndarray, sample_rate: int, from_frequency_hz: float) -> np.ndarray:
    if samples.size == 0:
        return samples
    alpha = float(np.exp(-2.0 * np.pi * max(from_frequency_hz, 1.0) / float(sample_rate)))
    emphasized = np.empty_like(samples)
    emphasized[0] = samples[0]
    emphasized[1:] = samples[1:] - (alpha * samples[:-1])
    return emphasized


def _gaussian_window(frame_size: int) -> np.ndarray:
    center = 0.5 * (frame_size - 1)
    sigma = max(frame_size / 6.0, 1.0)
    positions = np.arange(frame_size, dtype=np.float64)
    window = np.exp(-0.5 * ((positions - center) / sigma) ** 2.0)
    return np.asarray(window, dtype=np.float32)


def _pad_for_centered_stft(samples: np.ndarray, *, frame_size: int, hop: int) -> np.ndarray:
    half_window = frame_size // 2
    centered = np.pad(samples, (half_window, half_window), mode="constant")
    if centered.size < frame_size:
        return np.pad(centered, (0, frame_size - centered.size), mode="constant")

    remainder = (centered.size - frame_size) % hop
    if remainder == 0:
        return centered
    return np.pad(centered, (0, hop - remainder), mode="constant")


def _frame_signal(
    samples: np.ndarray,
    *,
    frame_size: int,
    hop: int,
    sample_rate: int,
    original_duration_seconds: float,
) -> tuple[np.ndarray, np.ndarray]:
    total_frames = 1 + ((samples.size - frame_size) // hop)
    if total_frames <= 0:
        return np.zeros((0, frame_size), dtype=np.float32), np.zeros(0, dtype=np.float32)

    starts = np.arange(total_frames, dtype=np.int64) * hop
    frame_center_times = starts.astype(np.float32) / float(sample_rate)
    valid_mask = frame_center_times <= max(original_duration_seconds, 0.0)
    if not np.any(valid_mask):
        valid_mask[0] = True
    starts = starts[valid_mask]
    frame_center_times = frame_center_times[valid_mask]
    indices = starts[:, None] + np.arange(frame_size, dtype=np.int64)[None, :]
    return samples[indices], frame_center_times


def _normalize_log_power(power: np.ndarray, *, dynamic_range_db: float) -> np.ndarray:
    power = np.maximum(power, EPSILON)
    db_values = 10.0 * np.log10(power)
    peak_db = float(np.max(db_values))
    effective_dynamic_range_db = max(1.0, float(dynamic_range_db))
    floor_db = peak_db - effective_dynamic_range_db
    clipped = np.clip(db_values, floor_db, peak_db)
    normalized = (clipped - floor_db) / effective_dynamic_range_db
    return np.asarray(normalized, dtype=np.float32)
