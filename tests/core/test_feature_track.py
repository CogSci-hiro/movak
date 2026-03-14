"""Feature track tests."""

import numpy as np

from movak.core.feature_track import FeatureTrack


def test_feature_track_samples_nearest_value() -> None:
    """Feature tracks return the nearest sampled point."""
    track = FeatureTrack(
        name="pitch",
        times=np.array([0.0, 0.1, 0.2], dtype=np.float64),
        values=np.array([100.0, 110.0, 120.0], dtype=np.float64),
    )

    assert track.sample_at(0.11) == 110.0
