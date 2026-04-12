"""Standalone subprocess worker for formant extraction."""

from __future__ import annotations

import sys

import numpy as np

from .formants import FormantSettings, build_formant_tracks


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        return 2

    input_path, output_path = args
    try:
        with np.load(input_path, allow_pickle=False) as payload:
            samples = payload["samples"].astype(np.float32, copy=False)
            sample_rate = int(payload["sample_rate"][0])
            sample_offset_seconds = float(payload["sample_offset_seconds"][0])
            settings_key = tuple(float(value) for value in payload["settings_key"].tolist())

        tracks = build_formant_tracks(
            samples,
            sample_rate,
            settings=FormantSettings(
                time_step_s=settings_key[0],
                max_number_of_formants=int(settings_key[1]),
                max_frequency_hz=settings_key[2],
                window_length_s=settings_key[3],
                preemphasis_from_hz=settings_key[4],
            ),
        )
        np.savez_compressed(
            output_path,
            ok=np.array([1], dtype=np.uint8),
            error_message=np.array([""], dtype=np.str_),
            times_seconds=(tracks.times_seconds + sample_offset_seconds).astype(np.float32, copy=False),
            frequencies_hz=tracks.frequencies_hz.astype(np.float32, copy=False),
            frame_confidence=tracks.frame_confidence.astype(np.float32, copy=False),
        )
        return 0
    except Exception as error:
        np.savez_compressed(
            output_path,
            ok=np.array([0], dtype=np.uint8),
            error_message=np.array([str(error)], dtype=np.str_),
            times_seconds=np.zeros(0, dtype=np.float32),
            frequencies_hz=np.zeros((0, 0), dtype=np.float32),
            frame_confidence=np.zeros(0, dtype=np.float32),
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
