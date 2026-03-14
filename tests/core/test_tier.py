"""Tier tests."""

from movak.core.interval import Interval
from movak.core.tier import Tier


def test_tier_keeps_intervals_sorted_by_start_time() -> None:
    """Tier insertion preserves sort order."""
    later = Interval(start=0.5, end=1.0, label="later")
    earlier = Interval(start=0.0, end=0.25, label="earlier")
    tier = Tier(name="phoneme")

    tier.add_interval(later)
    tier.add_interval(earlier)

    assert [interval.label for interval in tier.intervals] == ["earlier", "later"]


def test_tier_find_and_range_queries() -> None:
    """Tier lookup methods return matching intervals."""
    first = Interval(start=0.0, end=0.2, label="a")
    second = Interval(start=0.3, end=0.6, label="b")
    tier = Tier(name="phoneme", intervals=[first, second])

    assert tier.find_interval(first.token_id) is first
    assert tier.get_intervals_in_range(0.1, 0.4) == [first, second]
