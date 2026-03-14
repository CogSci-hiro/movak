"""Query filter helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class QueryFilter:
    """Represent a simple column-based predicate."""

    column: str
    operator: str
    value: Any

    def apply(self, frame: pd.DataFrame) -> pd.Series:
        """Apply the filter to a data frame.

        Parameters
        ----------
        frame
            Token index data frame.

        Returns
        -------
        pandas.Series
            Boolean mask for matching rows.
        """
        if self.column not in frame.columns:
            raise KeyError(f"Column '{self.column}' does not exist in the token index.")

        series = frame[self.column]
        if self.operator == "==":
            return series == self.value
        if self.operator == "!=":
            return series != self.value
        if self.operator == ">":
            return series > self.value
        if self.operator == ">=":
            return series >= self.value
        if self.operator == "<":
            return series < self.value
        if self.operator == "<=":
            return series <= self.value
        raise ValueError(f"Unsupported operator '{self.operator}'.")

    def matches(self, value: Any) -> bool:
        """Check whether a scalar value satisfies the predicate.

        Parameters
        ----------
        value
            Candidate value.

        Returns
        -------
        bool
            Match result.
        """
        scalar_frame = pd.DataFrame({self.column: [value]})
        return bool(self.apply(scalar_frame).iloc[0])
