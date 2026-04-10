"""Waveform cache and viewport-aware plotting helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .loader import EMPTY_SAMPLE_RATE, LoadedAudioData

MIN_VISIBLE_DURATION_SECONDS = 1e-6
POINTS_PER_PIXEL = 2
FULL_RESOLUTION_DENSITY_RATIO = 2


@dataclass(slots=True)
class WaveformPlotData:
    """Visible waveform data ready for plotting."""

    x_values: np.ndarray
    y_values: np.ndarray
    used_envelope: bool


@dataclass(slots=True)
class WaveformData:
    """Waveform samples and metadata prepared for GUI display."""

    samples: np.ndarray
    sample_rate: int
    duration_seconds: float
    channel_samples: np.ndarray | None = None
    channel_count: int = 1

    @property
    def sample_count(self) -> int:
        """Return the number of mono samples."""
        return int(self.samples.size)

    @property
    def has_stereo(self) -> bool:
        """Return whether two-channel source data is available."""
        return self.channel_samples is not None and self.channel_count >= 2


class WaveformCache:
    """Store the most recently loaded full-resolution waveform."""

    def __init__(self) -> None:
        self._current_waveform: WaveformData | None = None

    @property
    def current_waveform(self) -> WaveformData | None:
        """Return the currently cached waveform, if any."""
        return self._current_waveform

    def set_waveform(self, loaded_audio: LoadedAudioData) -> WaveformData:
        """Cache waveform data for the active audio file."""
        channel_samples = None
        if loaded_audio.channel_samples is not None:
            channel_samples = np.asarray(loaded_audio.channel_samples, dtype=np.float32)

        self._current_waveform = WaveformData(
            samples=np.asarray(loaded_audio.samples, dtype=np.float32),
            sample_rate=loaded_audio.sample_rate,
            duration_seconds=loaded_audio.duration_seconds,
            channel_samples=channel_samples,
            channel_count=max(1, int(loaded_audio.channel_count)),
        )
        return self._current_waveform

    def clear(self) -> None:
        """Clear cached waveform data."""
        self._current_waveform = None


def get_visible_waveform(
    samples: np.ndarray,
    sample_rate: int,
    start_time_s: float,
    end_time_s: float,
    target_num_points: int,
) -> WaveformPlotData:
    """Return plot data for the current visible waveform window.

    Parameters
    ----------
    samples
        Full-resolution mono waveform samples.
    sample_rate
        Sampling rate in Hz.
    start_time_s
        Visible window start in seconds.
    end_time_s
        Visible window end in seconds.
    target_num_points
        Approximate point budget derived from viewport width.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive.")
    if target_num_points <= 0:
        raise ValueError("target_num_points must be positive.")

    normalized_samples = np.asarray(samples, dtype=np.float32)
    sample_count = normalized_samples.size
    if sample_count == 0:
        return WaveformPlotData(
            x_values=np.zeros(0, dtype=np.float32),
            y_values=np.zeros(0, dtype=np.float32),
            used_envelope=False,
        )

    clamped_start_time = max(0.0, start_time_s)
    duration_seconds = sample_count / float(sample_rate)
    clamped_end_time = min(max(clamped_start_time + MIN_VISIBLE_DURATION_SECONDS, end_time_s), duration_seconds)

    start_index = max(0, min(sample_count, int(np.floor(clamped_start_time * sample_rate))))
    end_index = max(start_index + 1, min(sample_count, int(np.ceil(clamped_end_time * sample_rate))))
    visible_samples = normalized_samples[start_index:end_index]
    visible_sample_count = visible_samples.size

    if visible_sample_count <= target_num_points * FULL_RESOLUTION_DENSITY_RATIO:
        x_values = (np.arange(start_index, end_index, dtype=np.float32) / float(sample_rate))
        return WaveformPlotData(x_values=x_values, y_values=visible_samples, used_envelope=False)

    return _build_peak_envelope(
        visible_samples=visible_samples,
        sample_rate=sample_rate,
        start_index=start_index,
        target_num_points=target_num_points,
    )


def empty_waveform_data() -> WaveformData:
    """Return an empty waveform container for initial UI state."""
    empty_samples = np.zeros(0, dtype=np.float32)
    return WaveformData(
        samples=empty_samples,
        sample_rate=EMPTY_SAMPLE_RATE,
        duration_seconds=0.0,
        channel_samples=np.zeros((0, 1), dtype=np.float32),
        channel_count=1,
    )


def _build_peak_envelope(
    *,
    visible_samples: np.ndarray,
    sample_rate: int,
    start_index: int,
    target_num_points: int,
) -> WaveformPlotData:
    """Build a min/max envelope for a dense visible window."""
    bin_count = max(1, target_num_points // 2)
    sample_count = visible_samples.size
    padded_length = int(np.ceil(sample_count / bin_count) * bin_count)
    padding_width = padded_length - sample_count
    if padding_width > 0:
        padded_samples = np.pad(visible_samples, (0, padding_width), mode="edge")
    else:
        padded_samples = visible_samples

    reshaped_samples = padded_samples.reshape(bin_count, -1)
    min_values = reshaped_samples.min(axis=1)
    max_values = reshaped_samples.max(axis=1)

    samples_per_bin = reshaped_samples.shape[1]
    bin_start_indices = start_index + (np.arange(bin_count, dtype=np.float32) * samples_per_bin)
    x_values = np.repeat(bin_start_indices / float(sample_rate), 2)
    y_values = np.empty(bin_count * 2, dtype=np.float32)
    y_values[0::2] = min_values
    y_values[1::2] = max_values
    return WaveformPlotData(x_values=x_values, y_values=y_values, used_envelope=True)
