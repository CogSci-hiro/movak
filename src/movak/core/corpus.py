"""Core corpus model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from movak.core.recording import Recording
from movak.core.schema import AnnotationSchema
from movak.query.token_index import build_token_index


@dataclass(slots=True)
class Corpus:
    """Top-level Movak project container.

    Parameters
    ----------
    recordings
        Mapping of recording identifiers to recordings.
    metadata
        Corpus-level metadata.
    schema
        Optional annotation schema.
    """

    recordings: dict[str, Recording] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema: AnnotationSchema | None = None

    def add_recording(self, recording: Recording) -> None:
        """Add a recording to the corpus.

        Parameters
        ----------
        recording
            Recording instance to register.
        """
        if self.schema is not None:
            self.schema.validate_recording(recording)
        self.recordings[recording.id] = recording

    def get_recording(self, recording_id: str) -> Recording:
        """Load a recording by identifier.

        Parameters
        ----------
        recording_id
            Unique recording identifier.

        Returns
        -------
        Recording
            Matching recording.

        Raises
        ------
        KeyError
            Raised when the recording does not exist.
        """
        try:
            return self.recordings[recording_id]
        except KeyError as error:
            raise KeyError(f"Recording '{recording_id}' does not exist.") from error

    def build_token_index(self) -> pd.DataFrame:
        """Build a flattened token index for the corpus.

        Returns
        -------
        pandas.DataFrame
            Token index containing all corpus intervals.
        """
        return build_token_index(self)
