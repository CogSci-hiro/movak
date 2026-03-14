"""Query engine tests."""

from movak.core.corpus import Corpus
from movak.core.interval import Interval
from movak.core.recording import Recording
from movak.core.tier import Tier
from movak.query.filters import QueryFilter
from movak.query.query_engine import QueryEngine


def test_query_engine_filters_tokens_with_structured_filter() -> None:
    """Structured filters return matching rows."""
    short = Interval(start=0.0, end=0.1, label="p")
    long = Interval(start=0.1, end=0.5, label="a")
    corpus = Corpus(
        recordings={
            "rec-1": Recording(
                id="rec-1",
                tiers={"phoneme": Tier(name="phoneme", intervals=[short, long])},
            )
        }
    )
    engine = QueryEngine(corpus=corpus)

    results = engine.filter_tokens(QueryFilter(column="duration", operator=">", value=0.2))

    assert len(results) == 1
    assert results.loc[0, "label"] == "a"


def test_query_engine_finds_tokens_and_returns_intervals() -> None:
    """Query text resolves back to interval objects."""
    target = Interval(start=0.0, end=0.3, label="p")
    other = Interval(start=0.3, end=0.4, label="t")
    corpus = Corpus(
        recordings={
            "rec-1": Recording(
                id="rec-1",
                tiers={"phoneme": Tier(name="phoneme", intervals=[target, other])},
            )
        }
    )
    engine = QueryEngine(corpus=corpus)

    result_rows = engine.find_tokens('label == "p" and duration >= 0.3')
    result_intervals = engine.get_token_intervals('label == "p" and duration >= 0.3')

    assert len(result_rows) == 1
    assert result_rows.loc[0, "token_id"] == target.token_id
    assert result_intervals == [target]
