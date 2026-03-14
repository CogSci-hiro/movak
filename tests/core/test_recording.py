"""Recording tests."""

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier


def test_recording_add_tier_and_lookup_interval_by_id() -> None:
    """Recording resolves tiers and intervals."""
    interval = Interval(start=0.0, end=0.1, label="p")
    tier = Tier(name="phoneme", intervals=[interval])
    recording = Recording(id="rec-1")

    recording.add_tier(tier)
    resolved_tier_name, resolved_interval = recording.get_interval_by_id(interval.token_id) or ("", None)

    assert recording.get_tier("phoneme") is tier
    assert resolved_tier_name == "phoneme"
    assert resolved_interval is interval
