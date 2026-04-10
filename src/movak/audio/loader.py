"""Audio file loading helpers for playback and waveform display."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

SUPPORTED_AUDIO_PATTERNS = ("*.wav", "*.mp3", "*.flac", "*.ogg", "*.m4a")
OPEN_AUDIO_DIALOG_FILTER = (
    "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a);;"
    "WAV Files (*.wav);;"
    "MP3 Files (*.mp3);;"
    "FLAC Files (*.flac);;"
    "Ogg Files (*.ogg);;"
    "M4A Files (*.m4a);;"
    "All Files (*)"
)
EMPTY_SAMPLE_RATE = 1


@dataclass(slots=True)
class LoadedAudioData:
    """Normalized audio data for waveform display."""

    samples: np.ndarray
    sample_rate: int
    duration_seconds: float
    channel_samples: np.ndarray | None = None
    channel_count: int = 1


def normalize_local_audio_path(path: str) -> str:
    """Return a normalized local path or raise ``ValueError``."""
    normalized_path = Path(path).expanduser().resolve(strict=False)
    if not normalized_path.exists():
        raise ValueError(f"Audio file does not exist: {normalized_path}")
    if not normalized_path.is_file():
        raise ValueError(f"Audio path is not a file: {normalized_path}")
    return str(normalized_path)


def load_audio_for_waveform(path: str) -> LoadedAudioData:
    """Read local audio into a mono ``float32`` waveform array."""
    try:
        import soundfile as sf
    except ModuleNotFoundError as error:  # pragma: no cover - depends on runtime environment
        raise RuntimeError("python-soundfile is required for waveform loading.") from error

    normalized_path = normalize_local_audio_path(path)
    sample_matrix, sample_rate = sf.read(normalized_path, dtype="float32", always_2d=True)

    if sample_rate <= 0:
        raise ValueError("Audio file has an invalid sample rate.")
    if sample_matrix.ndim != 2:
        raise ValueError("Audio data must be two-dimensional after loading.")

    channel_samples = _normalize_channel_samples(sample_matrix)
    mono_samples = _mix_to_mono(channel_samples)
    duration_seconds = float(mono_samples.size) / float(sample_rate) if mono_samples.size > 0 else 0.0
    return LoadedAudioData(
        samples=mono_samples,
        sample_rate=int(sample_rate),
        duration_seconds=duration_seconds,
        channel_samples=channel_samples,
        channel_count=int(channel_samples.shape[1]) if channel_samples.ndim == 2 else 1,
    )


def _mix_to_mono(sample_matrix: np.ndarray) -> np.ndarray:
    """Convert multi-channel audio to a mono ``float32`` waveform."""
    if sample_matrix.size == 0:
        return np.zeros(0, dtype=np.float32)

    mono_samples = sample_matrix.mean(axis=1, dtype=np.float32)
    mono_samples = np.nan_to_num(mono_samples, nan=0.0, posinf=0.0, neginf=0.0)
    return np.asarray(mono_samples, dtype=np.float32)


def _normalize_channel_samples(sample_matrix: np.ndarray) -> np.ndarray:
    """Return sanitized per-channel samples with shape ``(num_samples, num_channels)``."""
    if sample_matrix.size == 0:
        return np.zeros((0, 1), dtype=np.float32)

    channel_samples = np.asarray(sample_matrix, dtype=np.float32)
    channel_samples = np.nan_to_num(channel_samples, nan=0.0, posinf=0.0, neginf=0.0)
    if channel_samples.ndim != 2:
        raise ValueError("Audio channel samples must be two-dimensional.")
    return channel_samples
