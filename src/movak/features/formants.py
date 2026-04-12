"""Praat-backed formant extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..audio.spectrogram import (
    PRAAT_DEFAULT_FORMANT_MAX_FREQUENCY_HZ,
    PRAAT_DEFAULT_FORMANT_PREEMPHASIS_FROM_HZ,
    PRAAT_DEFAULT_FORMANT_WINDOW_LENGTH_S,
    PRAAT_DEFAULT_MAX_NUMBER_OF_FORMANTS,
    PRAAT_DEFAULT_TIME_STEP_S,
)

FORMANT_CONFIDENCE_MIN_DB = -55.0
FORMANT_CONFIDENCE_MAX_DB = -25.0
FORMANT_UNVOICED_CONFIDENCE = 0.15
FORMANT_VOICED_CONFIDENCE = 1.0
FORMANT_SANITY_PARTIAL_PENALTY = 0.6
FORMANT_SANITY_REJECT_PENALTY = 0.0
PLAUSIBLE_F1_RANGE_HZ = (150.0, 1_200.0)
PLAUSIBLE_F2_RANGE_HZ = (500.0, 4_500.0)


@dataclass(slots=True)
class FormantSettings:
    """User-adjustable Praat formant analysis settings."""

    time_step_s: float = PRAAT_DEFAULT_TIME_STEP_S
    max_number_of_formants: int = PRAAT_DEFAULT_MAX_NUMBER_OF_FORMANTS
    max_frequency_hz: float = PRAAT_DEFAULT_FORMANT_MAX_FREQUENCY_HZ
    window_length_s: float = PRAAT_DEFAULT_FORMANT_WINDOW_LENGTH_S
    preemphasis_from_hz: float = PRAAT_DEFAULT_FORMANT_PREEMPHASIS_FROM_HZ


@dataclass(slots=True)
class FormantTracks:
    """Formant tracks ready for timeline display."""

    times_seconds: np.ndarray
    frequencies_hz: np.ndarray
    frame_confidence: np.ndarray
    backend_name: str = "Praat"


class FormantExtractor:
    """Extract formant tracks via Praat through parselmouth."""

    def compute(
        self,
        samples: np.ndarray,
        sample_rate: int,
        *,
        settings: FormantSettings | None = None,
    ) -> FormantTracks:
        return build_formant_tracks(samples, sample_rate, settings=settings)


def build_formant_tracks(
    samples: np.ndarray,
    sample_rate: int,
    *,
    settings: FormantSettings | None = None,
) -> FormantTracks:
    """Compute Praat Burg formants for a mono signal."""

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive.")

    active_settings = settings or FormantSettings()
    mono_samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if mono_samples.size == 0:
        return FormantTracks(
            times_seconds=np.zeros(0, dtype=np.float32),
            frequencies_hz=np.zeros((active_settings.max_number_of_formants, 0), dtype=np.float32),
            frame_confidence=np.zeros(0, dtype=np.float32),
        )

    parselmouth, praat_call = _load_parselmouth()
    sound = parselmouth.Sound(mono_samples, sampling_frequency=float(sample_rate))
    formant_object = praat_call(
        sound,
        "To Formant (burg)",
        float(max(active_settings.time_step_s, 1e-6)),
        float(max(active_settings.max_number_of_formants, 1)),
        float(max(active_settings.max_frequency_hz, 1.0)),
        float(max(active_settings.window_length_s, 1e-6)),
        float(max(active_settings.preemphasis_from_hz, 0.0)),
    )

    frame_count = int(praat_call(formant_object, "Get number of frames"))
    if frame_count <= 0:
        return FormantTracks(
            times_seconds=np.zeros(0, dtype=np.float32),
            frequencies_hz=np.zeros((active_settings.max_number_of_formants, 0), dtype=np.float32),
            frame_confidence=np.zeros(0, dtype=np.float32),
        )

    times_seconds = np.array(
        [float(praat_call(formant_object, "Get time from frame number", frame_index + 1)) for frame_index in range(frame_count)],
        dtype=np.float32,
    )
    frequencies_hz = np.full(
        (active_settings.max_number_of_formants, frame_count),
        np.nan,
        dtype=np.float32,
    )
    for formant_index in range(active_settings.max_number_of_formants):
        formant_number = formant_index + 1
        for frame_index, time_seconds in enumerate(times_seconds):
            value = float(praat_call(formant_object, "Get value at time", formant_number, float(time_seconds), "Hertz", "Linear"))
            if np.isfinite(value) and value > 0.0:
                frequencies_hz[formant_index, frame_index] = value

    frame_confidence = _compute_formant_display_confidence(
        mono_samples,
        sample_rate,
        times_seconds,
        frequencies_hz,
        frame_window_length_s=active_settings.window_length_s,
        praat_call=praat_call,
        sound=sound,
    )
    return FormantTracks(
        times_seconds=times_seconds,
        frequencies_hz=frequencies_hz,
        frame_confidence=frame_confidence,
    )


def _compute_formant_display_confidence(
    samples: np.ndarray,
    sample_rate: int,
    times_seconds: np.ndarray,
    frequencies_hz: np.ndarray,
    *,
    frame_window_length_s: float,
    praat_call,
    sound,
) -> np.ndarray:
    if times_seconds.size == 0:
        return np.zeros(0, dtype=np.float32)

    energy_confidence = _compute_energy_confidence(
        samples,
        sample_rate,
        times_seconds,
        frame_window_length_s=frame_window_length_s,
    )
    voicing_confidence = _compute_voicing_confidence(
        times_seconds,
        praat_call=praat_call,
        sound=sound,
    )
    sanity_confidence = _compute_sanity_confidence(frequencies_hz)
    confidence = energy_confidence * voicing_confidence * sanity_confidence
    return np.clip(confidence, 0.0, 1.0).astype(np.float32)


def _compute_energy_confidence(
    samples: np.ndarray,
    sample_rate: int,
    times_seconds: np.ndarray,
    *,
    frame_window_length_s: float,
) -> np.ndarray:
    frame_radius_samples = max(1, int(round(0.5 * frame_window_length_s * sample_rate)))
    confidence = np.zeros(times_seconds.size, dtype=np.float32)
    for frame_index, time_seconds in enumerate(times_seconds):
        center_sample = int(round(float(time_seconds) * sample_rate))
        start_sample = max(0, center_sample - frame_radius_samples)
        end_sample = min(samples.size, center_sample + frame_radius_samples)
        if end_sample <= start_sample:
            continue
        frame = samples[start_sample:end_sample].astype(np.float64, copy=False)
        rms = float(np.sqrt(np.mean(frame**2)))
        rms_db = 20.0 * np.log10(max(rms, np.finfo(np.float64).tiny))
        confidence[frame_index] = _normalize_linear(
            rms_db,
            minimum=FORMANT_CONFIDENCE_MIN_DB,
            maximum=FORMANT_CONFIDENCE_MAX_DB,
        )
    return confidence


def _compute_voicing_confidence(
    times_seconds: np.ndarray,
    *,
    praat_call,
    sound,
) -> np.ndarray:
    pitch_object = praat_call(sound, "To Pitch", 0.0, 75.0, 600.0)
    confidence = np.empty(times_seconds.size, dtype=np.float32)
    for frame_index, time_seconds in enumerate(times_seconds):
        pitch_hz = float(praat_call(pitch_object, "Get value at time", float(time_seconds), "Hertz", "Linear"))
        confidence[frame_index] = FORMANT_VOICED_CONFIDENCE if np.isfinite(pitch_hz) and pitch_hz > 0.0 else FORMANT_UNVOICED_CONFIDENCE
    return confidence


def _compute_sanity_confidence(frequencies_hz: np.ndarray) -> np.ndarray:
    if frequencies_hz.ndim != 2:
        return np.zeros(0, dtype=np.float32)

    frame_count = frequencies_hz.shape[1]
    confidence = np.ones(frame_count, dtype=np.float32)
    if frequencies_hz.shape[0] == 0:
        return np.zeros(frame_count, dtype=np.float32)

    missing_mask = np.any(~np.isfinite(frequencies_hz), axis=0)
    confidence[missing_mask] *= FORMANT_SANITY_PARTIAL_PENALTY

    if frequencies_hz.shape[0] >= 1:
        f1_values = frequencies_hz[0]
        invalid_f1_mask = (
            np.isfinite(f1_values)
            & ((f1_values < PLAUSIBLE_F1_RANGE_HZ[0]) | (f1_values > PLAUSIBLE_F1_RANGE_HZ[1]))
        )
        confidence[invalid_f1_mask] *= FORMANT_SANITY_PARTIAL_PENALTY

    if frequencies_hz.shape[0] >= 2:
        f1_values = frequencies_hz[0]
        f2_values = frequencies_hz[1]
        invalid_f2_mask = (
            np.isfinite(f2_values)
            & ((f2_values < PLAUSIBLE_F2_RANGE_HZ[0]) | (f2_values > PLAUSIBLE_F2_RANGE_HZ[1]))
        )
        crossed_mask = np.isfinite(f1_values) & np.isfinite(f2_values) & (f1_values >= f2_values)
        confidence[invalid_f2_mask] *= FORMANT_SANITY_PARTIAL_PENALTY
        confidence[crossed_mask] *= FORMANT_SANITY_REJECT_PENALTY

    return confidence


def _normalize_linear(value: float, *, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 0.0
    return min(max((value - minimum) / (maximum - minimum), 0.0), 1.0)


def _load_parselmouth():
    try:
        import parselmouth
        from parselmouth.praat import call as praat_call
    except ImportError as error:
        raise RuntimeError(
            "Formant plotting requires the optional 'praat-parselmouth' package."
        ) from error
    return parselmouth, praat_call
