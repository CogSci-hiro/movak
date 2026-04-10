from __future__ import annotations

import numpy as np
import pytest

from movak.audio.loader import LoadedAudioData, load_audio_for_waveform
from movak.audio.waveform_cache import WaveformCache, get_visible_waveform


def test_load_audio_for_waveform_converts_stereo_to_mono_and_tracks_duration(tmp_path):
    sf = pytest.importorskip("soundfile")
    sample_rate = 8_000
    stereo_samples = np.array(
        [
            [0.5, -0.5],
            [1.0, 0.0],
            [-1.0, 1.0],
            [0.25, 0.75],
        ],
        dtype=np.float32,
    )
    audio_path = tmp_path / "example.wav"
    sf.write(audio_path, stereo_samples, sample_rate)

    loaded_audio = load_audio_for_waveform(str(audio_path))

    assert loaded_audio.sample_rate == sample_rate
    assert loaded_audio.samples.dtype == np.float32
    assert np.allclose(loaded_audio.samples, np.array([0.0, 0.5, 0.0, 0.5], dtype=np.float32))
    assert loaded_audio.channel_count == 2
    assert loaded_audio.channel_samples is not None
    assert loaded_audio.channel_samples.shape == stereo_samples.shape
    assert loaded_audio.duration_seconds == 4 / sample_rate


def test_get_visible_waveform_uses_raw_samples_for_small_window():
    sample_rate = 10
    samples = np.arange(100, dtype=np.float32)

    visible_waveform = get_visible_waveform(
        samples,
        sample_rate,
        start_time_s=1.0,
        end_time_s=1.5,
        target_num_points=32,
    )

    assert visible_waveform.used_envelope is False
    assert np.array_equal(visible_waveform.y_values, samples[10:15])
    assert np.allclose(visible_waveform.x_values, np.array([1.0, 1.1, 1.2, 1.3, 1.4], dtype=np.float32))


def test_get_visible_waveform_builds_peak_envelope_for_dense_window():
    sample_rate = 100
    samples = np.tile(np.array([0.0, 1.0, -1.0, 0.5], dtype=np.float32), 100)

    visible_waveform = get_visible_waveform(
        samples,
        sample_rate,
        start_time_s=0.0,
        end_time_s=4.0,
        target_num_points=40,
    )

    assert visible_waveform.used_envelope is True
    assert visible_waveform.x_values.size == 40
    assert visible_waveform.y_values.size == 40
    assert np.all(visible_waveform.y_values[0::2] <= visible_waveform.y_values[1::2])
    assert np.min(visible_waveform.y_values) <= -1.0
    assert np.max(visible_waveform.y_values) >= 1.0


def test_zoomed_window_yields_more_detail_than_full_window_at_same_point_budget():
    sample_rate = 1_000
    samples = np.sin(np.linspace(0.0, 80.0 * np.pi, num=20_000, dtype=np.float32))

    full_window = get_visible_waveform(
        samples,
        sample_rate,
        start_time_s=0.0,
        end_time_s=20.0,
        target_num_points=200,
    )
    zoomed_window = get_visible_waveform(
        samples,
        sample_rate,
        start_time_s=4.0,
        end_time_s=4.2,
        target_num_points=200,
    )

    assert full_window.used_envelope is True
    assert zoomed_window.used_envelope is False
    full_density = full_window.y_values.size / 20.0
    zoomed_density = zoomed_window.y_values.size / 0.2
    assert zoomed_density > full_density


def test_waveform_cache_preserves_full_resolution_source_data():
    samples = np.linspace(-1.0, 1.0, num=10_000, dtype=np.float32)
    channel_samples = np.column_stack((samples, -samples)).astype(np.float32)
    cache = WaveformCache()
    waveform_data = cache.set_waveform(
        LoadedAudioData(
            samples=samples,
            sample_rate=16_000,
            duration_seconds=10_000 / 16_000,
            channel_samples=channel_samples,
            channel_count=2,
        )
    )

    assert waveform_data.sample_count == 10_000
    assert np.array_equal(waveform_data.samples, samples)
    assert waveform_data.channel_samples is not None
    assert np.array_equal(waveform_data.channel_samples, channel_samples)
    assert waveform_data.has_stereo is True
