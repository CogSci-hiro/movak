"""Corpus tests."""

from movak.core.corpus import Corpus
from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier


def test_corpus_builds_token_index() -> None:
    """Corpus exposes a flattened token index."""
    interval = Interval(start=0.0, end=0.1, label="p")
    tier = Tier(name="phoneme", intervals=[interval])
    recording = Recording(id="rec-1", tiers={"phoneme": tier})
    corpus = Corpus(recordings={"rec-1": recording})

    token_table = corpus.build_token_index()

    assert list(token_table.columns) == [
        "token_id",
        "recording",
        "tier",
        "label",
        "start",
        "end",
        "duration",
    ]
    assert token_table.loc[0, "recording"] == "rec-1"
