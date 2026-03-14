"""Recording model."""

from __future__ import annotations

from dataclasses import dataclass, field

from movak.core.feature_track import FeatureTrack
from movak.core.interval import Interval
from movak.core.tier import Tier


@dataclass(slots=True)
class Recording:
    """Audio recording and associated annotations.

    Parameters
    ----------
    id
        Unique recording identifier.
    audio_path
        Audio file path.
    tiers
        Annotation tiers keyed by name.
    features
        Feature tracks keyed by name.
    duration
        Recording duration in seconds.
    """

    id: str
    audio_path: str = ""
    tiers: dict[str, Tier] = field(default_factory=dict)
    features: dict[str, FeatureTrack] = field(default_factory=dict)
    duration: float = 0.0

    def add_tier(self, tier: Tier) -> None:
        """Attach a tier to the recording.

        Parameters
        ----------
        tier
            Tier instance to add.
        """
        self.tiers[tier.name] = tier

    def get_tier(self, tier_name: str) -> Tier:
        """Return a tier by name.

        Parameters
        ----------
        tier_name
            Tier name to resolve.

        Returns
        -------
        Tier
            Matching tier.

        Raises
        ------
        KeyError
            Raised when the tier does not exist.
        """
        try:
            return self.tiers[tier_name]
        except KeyError as error:
            raise KeyError(f"Tier '{tier_name}' does not exist in recording '{self.id}'.") from error

    def add_feature_track(self, feature_track: FeatureTrack) -> None:
        """Attach a feature track to the recording.

        Parameters
        ----------
        feature_track
            Track instance to add.
        """
        self.features[feature_track.name] = feature_track

    def get_interval_by_id(self, token_id: str) -> tuple[str, Interval] | None:
        """Return an interval by token identifier.

        Parameters
        ----------
        token_id
            Token identifier to resolve.

        Returns
        -------
        tuple[str, Interval] | None
            A tuple of tier name and interval, or ``None`` when absent.
        """
        for tier_name, tier in self.tiers.items():
            interval = tier.find_interval(token_id)
            if interval is not None:
                return tier_name, interval
        return None
