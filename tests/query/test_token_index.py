"""Token index tests."""

from movak.core.corpus import Corpus
from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.query.token_index import TokenIndex, build_token_index


def test_build_token_index_generates_expected_rows() -> None:
    """Token index generation flattens all intervals."""
    interval = Interval(start=0.0, end=0.25, label="p")
    corpus = Corpus(
        recordings={
            "rec-1": Recording(
                id="rec-1",
                tiers={"phoneme": Tier(name="phoneme", intervals=[interval])},
            )
        }
    )

    token_table = build_token_index(corpus)

    assert len(token_table) == 1
    assert token_table.loc[0, "label"] == "p"
    assert token_table.loc[0, "duration"] == 0.25


def test_token_index_search_returns_matching_token_ids() -> None:
    """Token index search resolves token identifiers by label."""
    interval = Interval(start=0.0, end=0.25, label="p")
    corpus = Corpus(
        recordings={
            "rec-1": Recording(
                id="rec-1",
                tiers={"phoneme": Tier(name="phoneme", intervals=[interval])},
            )
        }
    )
    token_index = TokenIndex()
    token_index.build(corpus)

    assert token_index.search("p") == [interval.token_id]
