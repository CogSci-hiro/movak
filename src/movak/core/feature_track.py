"""Feature track model."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(slots=True)
class FeatureTrack:
    """Time-aligned numeric feature track.

    Parameters
    ----------
    name
        Track name.
    times
        Time stamps in seconds.
    values
        Feature values aligned to ``times``.
    """

    name: str
    times: FloatArray = field(default_factory=lambda: np.array([], dtype=np.float64))
    values: FloatArray = field(default_factory=lambda: np.array([], dtype=np.float64))

    def __post_init__(self) -> None:
        """Validate and normalize numpy arrays."""
        self.times = np.asarray(self.times, dtype=np.float64)
        self.values = np.asarray(self.values, dtype=np.float64)
        if self.times.shape != self.values.shape:
            raise ValueError("Feature track times and values must have matching shapes.")
        if self.times.ndim != 1:
            raise ValueError("Feature track arrays must be one-dimensional.")

    def sample_at(self, time_point: float) -> float:
        """Return the nearest sampled value at the requested time.

        Parameters
        ----------
        time_point
            Query time in seconds.

        Returns
        -------
        float
            Sampled feature value.

        Raises
        ------
        ValueError
            Raised when the track contains no samples.
        """
        if self.times.size == 0:
            raise ValueError("Cannot sample an empty feature track.")
        sample_index = int(np.abs(self.times - time_point).argmin())
        return float(self.values[sample_index])
