"""Base operation types."""

from __future__ import annotations

from abc import ABC, abstractmethod

from movak.core.recording import Recording


class Operation(ABC):
    """Base class for editable operations."""

    @abstractmethod
    def apply(self, recording: Recording) -> None:
        """Apply the operation to a recording.

        Parameters
        ----------
        recording
            Recording to mutate.
        """

    @abstractmethod
    def undo(self, recording: Recording) -> None:
        """Undo the operation on a recording.

        Parameters
        ----------
        recording
            Recording to mutate.
        """
