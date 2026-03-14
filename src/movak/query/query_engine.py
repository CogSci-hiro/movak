"""Query engine implementation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from movak.core.corpus import Corpus
from movak.core.interval import Interval
from movak.query.filters import QueryFilter


@dataclass(slots=True)
class QueryEngine:
    """Execute corpus queries against a token index."""

    corpus: Corpus

    def filter_tokens(self, query_filter: QueryFilter) -> pd.DataFrame:
        """Filter tokens using a structured query filter.

        Parameters
        ----------
        query_filter
            Filter predicate to apply.

        Returns
        -------
        pandas.DataFrame
            Filtered token rows.
        """
        token_table = self.corpus.build_token_index()
        mask = query_filter.apply(token_table)
        return token_table.loc[mask].reset_index(drop=True)

    def find_tokens(self, query_text: str) -> pd.DataFrame:
        """Filter tokens using a pandas query expression.

        Parameters
        ----------
        query_text
            Query expression, for example ``label == "p" and duration > 0.2``.

        Returns
        -------
        pandas.DataFrame
            Matching token rows.
        """
        token_table = self.corpus.build_token_index()
        if token_table.empty:
            return token_table
        return token_table.query(query_text).reset_index(drop=True)

    def get_token_intervals(self, query_text: str) -> list[Interval]:
        """Resolve queried tokens back to interval objects.

        Parameters
        ----------
        query_text
            Query expression.

        Returns
        -------
        list[Interval]
            Matching interval objects.
        """
        matching_rows = self.find_tokens(query_text)
        intervals: list[Interval] = []
        for row in matching_rows.itertuples(index=False):
            recording = self.corpus.get_recording(str(row.recording))
            interval_entry = recording.get_interval_by_id(str(row.token_id))
            if interval_entry is not None:
                _, interval = interval_entry
                intervals.append(interval)
        return intervals
