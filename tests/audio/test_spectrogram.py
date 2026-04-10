from __future__ import annotations

import numpy as np

from movak.audio.spectrogram import build_spectrogram


def test_build_spectrogram_returns_normalized_image_for_signal():
    sample_rate = 16_000
    duration_seconds = 1.0
    time_values = np.linspace(0.0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False, dtype=np.float32)
    samples = np.sin(2.0 * np.pi * 440.0 * time_values).astype(np.float32)

    result = build_spectrogram(samples, sample_rate)

    assert result.magnitude.ndim == 2
    assert result.magnitude.shape[0] > 0
    assert result.magnitude.shape[1] > 0
    assert result.frequency_hz.ndim == 1
    assert result.frequency_hz.size == result.magnitude.shape[0]
    assert result.frame_step_seconds > 0.0
    assert np.min(result.magnitude) >= 0.0
    assert np.max(result.magnitude) <= 1.0
    assert abs(result.duration_seconds - duration_seconds) < 1e-6


def test_build_spectrogram_keeps_tone_energy_near_target_frequency():
    sample_rate = 16_000
    duration_seconds = 0.8
    tone_hz = 440.0
    time_values = np.linspace(0.0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False, dtype=np.float32)
    samples = np.sin(2.0 * np.pi * tone_hz * time_values).astype(np.float32)

    result = build_spectrogram(samples, sample_rate)
    per_band_energy = result.magnitude.mean(axis=1)
    dominant_frequency = float(result.frequency_hz[int(np.argmax(per_band_energy))])

    assert abs(dominant_frequency - tone_hz) < 80.0


def test_build_spectrogram_has_dense_frequency_and_time_grid():
    sample_rate = 16_000
    duration_seconds = 1.0
    samples = np.sin(
        2.0 * np.pi * 220.0 * np.linspace(0.0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False, dtype=np.float32)
    ).astype(np.float32)

    result = build_spectrogram(samples, sample_rate)

    assert result.magnitude.shape[0] >= 300
    assert result.magnitude.shape[1] >= 400


def test_build_spectrogram_reports_ordered_frame_bounds_within_audio_extent():
    sample_rate = 16_000
    duration_seconds = 0.4
    samples = np.sin(
        2.0 * np.pi * 330.0 * np.linspace(0.0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False, dtype=np.float32)
    ).astype(np.float32)

    result = build_spectrogram(samples, sample_rate)

    assert 0.0 <= result.frame_start_seconds <= duration_seconds
    assert result.frame_end_seconds > result.frame_start_seconds
    assert result.frame_end_seconds <= duration_seconds + result.frame_step_seconds


def test_build_spectrogram_handles_empty_input():
    result = build_spectrogram(np.zeros(0, dtype=np.float32), sample_rate=16_000)

    assert result.magnitude.ndim == 2
    assert result.magnitude.shape[1] == 1
    assert result.frequency_hz.ndim == 1
    assert result.frequency_hz.size == result.magnitude.shape[0]
    assert result.duration_seconds == 0.0
