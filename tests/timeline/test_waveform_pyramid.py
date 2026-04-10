"""Waveform pyramid tests."""

from __future__ import annotations

import numpy as np

from movak.timeline.waveform_pyramid import WaveformPyramid


def test_waveform_pyramid_builds_multiple_levels() -> None:
    """Waveform pyramids contain progressively coarser levels."""

    audio_array = np.linspace(-1.0, 1.0, 64, dtype=np.float64)

    pyramid = WaveformPyramid.build(audio_array, sample_rate=16)

    assert len(pyramid.levels) >= 3
    assert pyramid.levels[0].block_size == 1
    assert pyramid.levels[1].block_size == 2


def test_waveform_pyramid_selects_coarser_level_when_zoomed_out() -> None:
    """Lower zoom levels use coarser waveform summaries."""

    audio_array = np.sin(np.linspace(0.0, 20.0, 4096, dtype=np.float64))
    pyramid = WaveformPyramid.build(audio_array, sample_rate=2048)

    detailed_level = pyramid.get_level(pixels_per_second=1000.0)
    coarse_level = pyramid.get_level(pixels_per_second=10.0)

    assert detailed_level.block_size < coarse_level.block_size


def test_waveform_pyramid_returns_visible_segment() -> None:
    """Segment extraction only returns the requested visible portion."""

    audio_array = np.arange(32, dtype=np.float64)
    pyramid = WaveformPyramid.build(audio_array, sample_rate=8)

    segment = pyramid.get_segment(1.0, 2.0, pixels_per_second=50.0)

    assert segment.time_values[0] >= 1.0
    assert segment.time_values[-1] < 2.0
    assert segment.min_values.size == segment.max_values.size
