import numpy as np
import pytest

from movak.audio.waveform_cache import WaveformData
from movak.features.analysis_inspector import (
    ANALYSIS_WINDOW_DURATION_S,
    FormantPoint,
    build_analysis_snapshot,
    compute_power_spectral_density,
    estimate_representative_formants,
    estimate_representative_formant_summary,
    extract_analysis_window,
)
from movak.features.formants import FormantTracks


def test_extract_analysis_window_clamps_near_audio_start():
    sample_rate = 4_000
    waveform_data = WaveformData(
        samples=np.linspace(-1.0, 1.0, sample_rate, dtype=np.float32),
        sample_rate=sample_rate,
        duration_seconds=1.0,
    )

    analysis_window = extract_analysis_window(waveform_data, 0.0)

    assert analysis_window is not None
    assert analysis_window.start_time_s == 0.0
    assert analysis_window.end_time_s <= ANALYSIS_WINDOW_DURATION_S
    assert analysis_window.samples.size == int(round(ANALYSIS_WINDOW_DURATION_S * sample_rate))


def test_compute_power_spectral_density_reports_frequency_peak():
    sample_rate = 8_000
    duration_s = 0.08
    time_axis = np.arange(int(sample_rate * duration_s), dtype=np.float64) / float(sample_rate)
    samples = np.sin(2.0 * np.pi * 440.0 * time_axis).astype(np.float32)

    estimate = compute_power_spectral_density(samples, sample_rate)

    assert estimate is not None
    peak_frequency_hz = float(estimate.frequencies_hz[np.argmax(estimate.power_db)])
    assert peak_frequency_hz == pytest.approx(440.0, abs=80.0)


def test_estimate_representative_formants_returns_none_when_backend_fails(monkeypatch):
    def raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("parselmouth unavailable")

    monkeypatch.setattr("movak.features.analysis_inspector.build_formant_tracks", raise_runtime_error)

    formant_point = estimate_representative_formants(np.ones(512, dtype=np.float32), 16_000)

    assert formant_point is None


def test_estimate_representative_formants_returns_median_pair(monkeypatch):
    def fake_build_formant_tracks(*_args, **_kwargs):
        return FormantTracks(
            times_seconds=np.array([0.0, 0.01, 0.02], dtype=np.float32),
            frequencies_hz=np.array(
                [
                    [500.0, 520.0, np.nan],
                    [1_500.0, 1_540.0, 1_560.0],
                ],
                dtype=np.float32,
            ),
            frame_confidence=np.ones(3, dtype=np.float32),
        )

    monkeypatch.setattr("movak.features.analysis_inspector.build_formant_tracks", fake_build_formant_tracks)

    formant_point = estimate_representative_formants(np.ones(512, dtype=np.float32), 16_000)

    assert formant_point == FormantPoint(f1_hz=510.0, f2_hz=1_520.0)


def test_estimate_representative_formants_uses_alpha_weighted_average(monkeypatch):
    def fake_build_formant_tracks(*_args, **_kwargs):
        return FormantTracks(
            times_seconds=np.array([0.0, 0.01, 0.02], dtype=np.float32),
            frequencies_hz=np.array(
                [
                    [400.0, 700.0, 1_000.0],
                    [1_200.0, 1_600.0, 2_100.0],
                ],
                dtype=np.float32,
            ),
            frame_confidence=np.array([0.0, 0.5, 1.0], dtype=np.float32),
        )

    monkeypatch.setattr("movak.features.analysis_inspector.build_formant_tracks", fake_build_formant_tracks)

    formant_point = estimate_representative_formants(np.ones(512, dtype=np.float32), 16_000)

    assert formant_point is not None
    assert formant_point.f1_hz == pytest.approx(879.18237, abs=1e-3)
    assert formant_point.f2_hz == pytest.approx(1_906.3440, abs=1e-3)


def test_estimate_representative_formant_summary_returns_marker_frequencies(monkeypatch):
    def fake_build_formant_tracks(*_args, **_kwargs):
        return FormantTracks(
            times_seconds=np.array([0.0, 0.01, 0.02], dtype=np.float32),
            frequencies_hz=np.array(
                [
                    [500.0, 520.0, np.nan],
                    [1_500.0, 1_540.0, 1_560.0],
                    [2_300.0, np.nan, 2_500.0],
                ],
                dtype=np.float32,
            ),
            frame_confidence=np.ones(3, dtype=np.float32),
        )

    monkeypatch.setattr("movak.features.analysis_inspector.build_formant_tracks", fake_build_formant_tracks)

    summary = estimate_representative_formant_summary(np.ones(512, dtype=np.float32), 16_000)

    assert summary.point == FormantPoint(f1_hz=510.0, f2_hz=1_520.0)
    assert summary.frequencies_hz == pytest.approx(np.array([510.0, 1_533.3334, 2_400.0], dtype=np.float32))
    assert summary.confidence == pytest.approx(1.0)


def test_estimate_representative_formant_summary_reports_weighted_confidence(monkeypatch):
    def fake_build_formant_tracks(*_args, **_kwargs):
        return FormantTracks(
            times_seconds=np.array([0.0, 0.01, 0.02], dtype=np.float32),
            frequencies_hz=np.array(
                [
                    [400.0, 700.0, 1_000.0],
                    [1_200.0, 1_600.0, 2_100.0],
                ],
                dtype=np.float32,
            ),
            frame_confidence=np.array([0.0, 0.5, 1.0], dtype=np.float32),
        )

    monkeypatch.setattr("movak.features.analysis_inspector.build_formant_tracks", fake_build_formant_tracks)

    summary = estimate_representative_formant_summary(np.ones(512, dtype=np.float32), 16_000)

    assert summary.confidence == pytest.approx(0.7986372, abs=1e-6)


def test_build_analysis_snapshot_exposes_formant_frequencies(monkeypatch):
    sample_rate = 8_000
    waveform_data = WaveformData(
        samples=np.ones(int(sample_rate * 0.2), dtype=np.float32),
        sample_rate=sample_rate,
        duration_seconds=0.2,
    )

    monkeypatch.setattr(
        "movak.features.analysis_inspector.compute_power_spectral_density",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "movak.features.analysis_inspector.estimate_representative_formant_summary",
        lambda *_args, **_kwargs: type(
            "FakeSummary",
            (),
            {
                "point": FormantPoint(f1_hz=450.0, f2_hz=1_350.0),
                "frequencies_hz": np.array([450.0, 1_350.0, 2_450.0], dtype=np.float32),
                "confidence": 0.4,
            },
        )(),
    )

    snapshot = build_analysis_snapshot(waveform_data, 0.1)

    assert snapshot.formant == FormantPoint(f1_hz=450.0, f2_hz=1_350.0)
    assert snapshot.formant_frequencies_hz == pytest.approx(np.array([450.0, 1_350.0, 2_450.0], dtype=np.float32))
    assert snapshot.formant_confidence == pytest.approx(0.4)
