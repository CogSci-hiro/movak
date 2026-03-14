"""Schema tests."""

import pytest

from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.schema import AnnotationSchema
from movak.core.tier import Tier


def test_schema_accepts_nested_hierarchy() -> None:
    """Schema validation accepts child intervals within parents."""
    phoneme = Tier(
        name="phoneme",
        parent_tier="word",
        intervals=[Interval(start=0.0, end=0.2, label="p")],
    )
    word = Tier(name="word", intervals=[Interval(start=0.0, end=0.5, label="pa")])
    recording = Recording(id="rec-1", tiers={"phoneme": phoneme, "word": word})
    schema = AnnotationSchema(tier_order=["phoneme", "word"])

    schema.validate_recording(recording)


def test_schema_rejects_child_interval_outside_parent() -> None:
    """Schema validation rejects hierarchy violations."""
    phoneme = Tier(
        name="phoneme",
        parent_tier="word",
        intervals=[Interval(start=0.6, end=0.8, label="p")],
    )
    word = Tier(name="word", intervals=[Interval(start=0.0, end=0.5, label="pa")])
    recording = Recording(id="rec-1", tiers={"phoneme": phoneme, "word": word})
    schema = AnnotationSchema(tier_order=["phoneme", "word"])

    with pytest.raises(ValueError):
        schema.validate_recording(recording)
