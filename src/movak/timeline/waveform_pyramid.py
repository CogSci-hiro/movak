"""Waveform multi-resolution caches for fast timeline rendering."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

MIN_LEVEL_BLOCK_SIZE = 1
MAX_POINTS_PER_PIXEL = 2.0


@dataclass(slots=True)
class WaveformPyramidLevel:
    """Single waveform pyramid level.

    Parameters
    ----------
    level_index
        Pyramid level index.
    block_size
        Number of original samples summarized by each min/max entry.
    min_values
        Minimum value for each block.
    max_values
        Maximum value for each block.
    """

    level_index: int
    block_size: int
    min_values: FloatArray
    max_values: FloatArray


@dataclass(slots=True)
class WaveformSegment:
    """Visible waveform envelope extracted from a pyramid level."""

    time_values: FloatArray
    min_values: FloatArray
    max_values: FloatArray
    level_index: int
    block_size: int


class WaveformPyramid:
    """Multi-resolution waveform cache for fast redraws.

    Parameters
    ----------
    sample_rate
        Sampling rate in Hz.
    levels
        Ordered waveform pyramid levels.
    """

    def __init__(self, sample_rate: int, levels: list[WaveformPyramidLevel]) -> None:
        self.sample_rate = sample_rate
        self.levels = levels

    @classmethod
    def build(
        cls,
        audio_array: np.ndarray,
        sample_rate: int,
        *,
        max_levels: int | None = None,
    ) -> "WaveformPyramid":
        """Build a min/max waveform pyramid from audio samples.

        Parameters
        ----------
        audio_array
            Audio samples. Mono arrays are expected; multi-channel input is averaged.
        sample_rate
            Sampling rate in Hz.
        max_levels
            Optional cap on the number of pyramid levels.
        """

        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive.")

        normalized_audio = _normalize_audio(audio_array)
        if normalized_audio.size == 0:
            normalized_audio = np.zeros(1, dtype=np.float64)

        levels: list[WaveformPyramidLevel] = []
        block_size = MIN_LEVEL_BLOCK_SIZE
        level_index = 0
        while True:
            level = _build_level(normalized_audio, level_index, block_size)
            levels.append(level)

            if max_levels is not None and len(levels) >= max_levels:
                break
            if level.min_values.size <= 1:
                break

            block_size *= 2
            level_index += 1

        return cls(sample_rate=sample_rate, levels=levels)

    def get_level(self, pixels_per_second: float) -> WaveformPyramidLevel:
        """Return the most appropriate level for the current zoom.

        Parameters
        ----------
        pixels_per_second
            Horizontal zoom level.
        """

        if pixels_per_second <= 0.0:
            raise ValueError("pixels_per_second must be positive.")

        target_points_per_second = pixels_per_second * MAX_POINTS_PER_PIXEL
        for level in self.levels:
            blocks_per_second = self.sample_rate / level.block_size
            if blocks_per_second <= target_points_per_second:
                return level
        return self.levels[-1]

    def get_segment(
        self,
        start_time: float,
        end_time: float,
        pixels_per_second: float,
    ) -> WaveformSegment:
        """Return a visible waveform segment for the active viewport.

        Parameters
        ----------
        start_time
            Visible start time in seconds.
        end_time
            Visible end time in seconds.
        pixels_per_second
            Horizontal zoom level.
        """

        if end_time <= start_time:
            raise ValueError("end_time must be greater than start_time.")

        level = self.get_level(pixels_per_second)
        start_index = max(int(np.floor(start_time * self.sample_rate / level.block_size)), 0)
        end_index = min(
            int(np.ceil(end_time * self.sample_rate / level.block_size)),
            level.min_values.size,
        )

        segment_min_values = level.min_values[start_index:end_index]
        segment_max_values = level.max_values[start_index:end_index]
        time_values = (
            (np.arange(start_index, end_index, dtype=np.float64) * level.block_size)
            / float(self.sample_rate)
        )

        return WaveformSegment(
            time_values=time_values,
            min_values=segment_min_values,
            max_values=segment_max_values,
            level_index=level.level_index,
            block_size=level.block_size,
        )


def _normalize_audio(audio_array: np.ndarray) -> FloatArray:
    """Return a mono float64 waveform array."""

    normalized_audio = np.asarray(audio_array, dtype=np.float64)
    if normalized_audio.ndim == 2:
        normalized_audio = normalized_audio.mean(axis=1)
    if normalized_audio.ndim != 1:
        raise ValueError("audio_array must be 1D or 2D with channels on the last axis.")
    return normalized_audio


def _build_level(audio_array: FloatArray, level_index: int, block_size: int) -> WaveformPyramidLevel:
    """Build one min/max pyramid level."""

    block_count = int(np.ceil(audio_array.size / block_size))
    padded_length = block_count * block_size
    padding_width = padded_length - audio_array.size
    if padding_width:
        padded_audio = np.pad(audio_array, (0, padding_width), mode="edge")
    else:
        padded_audio = audio_array

    reshaped_audio = padded_audio.reshape(block_count, block_size)
    min_values = reshaped_audio.min(axis=1)
    max_values = reshaped_audio.max(axis=1)

    return WaveformPyramidLevel(
        level_index=level_index,
        block_size=block_size,
        min_values=min_values,
        max_values=max_values,
    )
