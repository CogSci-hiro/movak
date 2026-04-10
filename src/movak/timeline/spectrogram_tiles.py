"""Spectrogram tiling for large timeline recordings."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.signal import stft

from movak.timeline.tile_cache import TileCache

FloatArray = NDArray[np.float64]

DEFAULT_TILE_DURATION = 2.0
DEFAULT_WINDOW_SIZE = 512
DEFAULT_HOP_SIZE = 128
DEFAULT_MAX_CACHE_ITEMS = 96
DEFAULT_MAX_CACHE_BYTES = 96 * 1024 * 1024


@dataclass(slots=True)
class SpectrogramTile:
    """One cached spectrogram tile."""

    tile_index: int
    start_time: float
    end_time: float
    time_values: FloatArray
    frequency_values: FloatArray
    magnitude: FloatArray


class SpectrogramTileManager:
    """Build and cache fixed-duration spectrogram tiles.

    Parameters
    ----------
    audio_array
        Mono audio samples.
    sample_rate
        Sampling rate in Hz.
    tile_duration
        Duration of each tile in seconds.
    window_size
        STFT window size.
    hop_size
        STFT hop size.
    cache
        Optional tile cache instance.
    """

    def __init__(
        self,
        audio_array: np.ndarray,
        sample_rate: int,
        *,
        tile_duration: float = DEFAULT_TILE_DURATION,
        window_size: int = DEFAULT_WINDOW_SIZE,
        hop_size: int = DEFAULT_HOP_SIZE,
        cache: TileCache[SpectrogramTile] | None = None,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive.")
        if tile_duration <= 0.0:
            raise ValueError("tile_duration must be positive.")
        if hop_size <= 0:
            raise ValueError("hop_size must be positive.")
        if window_size <= 0:
            raise ValueError("window_size must be positive.")

        self.audio_array = _normalize_audio(audio_array)
        self.sample_rate = sample_rate
        self.tile_duration = tile_duration
        self.window_size = window_size
        self.hop_size = hop_size
        self.cache = cache or TileCache(
            max_items=DEFAULT_MAX_CACHE_ITEMS,
            max_bytes=DEFAULT_MAX_CACHE_BYTES,
        )

    def build(self) -> None:
        """Prime the cache metadata without rendering all tiles eagerly."""

        self.cache.clear()

    def get_tiles(self, start_time: float, end_time: float) -> list[SpectrogramTile]:
        """Return the spectrogram tiles overlapping a time range."""

        if end_time <= start_time:
            raise ValueError("end_time must be greater than start_time.")

        first_tile_index = max(int(np.floor(start_time / self.tile_duration)), 0)
        last_tile_index = max(int(np.floor((end_time - 1e-9) / self.tile_duration)), first_tile_index)

        return [
            self._get_or_build_tile(tile_index)
            for tile_index in range(first_tile_index, last_tile_index + 1)
        ]

    def _get_or_build_tile(self, tile_index: int) -> SpectrogramTile:
        """Return one cached tile or compute it on demand."""

        cached_tile = self.cache.get(tile_index)
        if cached_tile is not None:
            return cached_tile

        tile = self._build_tile(tile_index)
        self.cache.put(tile_index, tile, _estimate_tile_size_bytes(tile))
        return tile

    def _build_tile(self, tile_index: int) -> SpectrogramTile:
        """Compute a spectrogram tile from the backing audio."""

        start_time = tile_index * self.tile_duration
        end_time = start_time + self.tile_duration
        start_sample = int(start_time * self.sample_rate)
        end_sample = min(int(end_time * self.sample_rate), self.audio_array.size)
        tile_audio = self.audio_array[start_sample:end_sample]

        if tile_audio.size == 0:
            frequency_values = np.linspace(0.0, self.sample_rate / 2.0, self.window_size // 2 + 1)
            return SpectrogramTile(
                tile_index=tile_index,
                start_time=start_time,
                end_time=end_time,
                time_values=np.array([], dtype=np.float64),
                frequency_values=frequency_values,
                magnitude=np.zeros((frequency_values.size, 0), dtype=np.float64),
            )

        frequency_values, relative_time_values, spectrum = stft(
            tile_audio,
            fs=self.sample_rate,
            nperseg=self.window_size,
            noverlap=max(self.window_size - self.hop_size, 0),
            boundary=None,
        )
        magnitude = np.abs(spectrum).astype(np.float64, copy=False)
        time_values = relative_time_values + start_time

        return SpectrogramTile(
            tile_index=tile_index,
            start_time=start_time,
            end_time=end_time,
            time_values=time_values,
            frequency_values=frequency_values.astype(np.float64, copy=False),
            magnitude=magnitude,
        )


def _normalize_audio(audio_array: np.ndarray) -> FloatArray:
    """Normalize audio input to mono float64."""

    normalized_audio = np.asarray(audio_array, dtype=np.float64)
    if normalized_audio.ndim == 2:
        normalized_audio = normalized_audio.mean(axis=1)
    if normalized_audio.ndim != 1:
        raise ValueError("audio_array must be 1D or 2D.")
    return normalized_audio


def _estimate_tile_size_bytes(tile: SpectrogramTile) -> int:
    """Approximate the memory footprint of a tile."""

    return tile.magnitude.nbytes + tile.time_values.nbytes + tile.frequency_values.nbytes
