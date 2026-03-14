"""Token index utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from movak.core.corpus import Corpus

TOKEN_INDEX_COLUMNS: tuple[str, ...] = (
    "token_id",
    "recording",
    "tier",
    "label",
    "start",
    "end",
    "duration",
)


def build_token_index(corpus: Corpus) -> pd.DataFrame:
    """Build a flattened token index for a corpus.

    Parameters
    ----------
    corpus
        Corpus to index.

    Returns
    -------
    pandas.DataFrame
        Data frame containing one row per interval.
    """
    rows: list[dict[str, str | float]] = []
    for recording_id, recording in corpus.recordings.items():
        for tier_name, tier in recording.tiers.items():
            for interval in tier.intervals:
                rows.append(
                    {
                        "token_id": interval.token_id,
                        "recording": recording_id,
                        "tier": tier_name,
                        "label": interval.label,
                        "start": interval.start,
                        "end": interval.end,
                        "duration": interval.duration(),
                    }
                )

    if not rows:
        return pd.DataFrame(columns=list(TOKEN_INDEX_COLUMNS))

    token_table = pd.DataFrame(rows, columns=list(TOKEN_INDEX_COLUMNS))
    return token_table.sort_values(["recording", "tier", "start", "end"]).reset_index(drop=True)


@dataclass(slots=True)
class TokenIndex:
    """In-memory token index wrapper."""

    table: pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(columns=list(TOKEN_INDEX_COLUMNS))
    )

    def build(self, corpus: Corpus) -> pd.DataFrame:
        """Build the token index from a corpus.

        Parameters
        ----------
        corpus
            Corpus to index.

        Returns
        -------
        pandas.DataFrame
            Built token index.
        """
        self.table = build_token_index(corpus)
        return self.table

    def search(self, token: str) -> list[str]:
        """Search the index for matching labels.

        Parameters
        ----------
        token
            Token label to query.

        Returns
        -------
        list[str]
            Matching token identifiers.
        """
        if self.table.empty:
            return []
        matching_rows = self.table[self.table["label"] == token]
        return matching_rows["token_id"].astype(str).tolist()
