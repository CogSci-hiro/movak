"""Undo and redo history."""

from __future__ import annotations

from dataclasses import dataclass, field

from movak.core.recording import Recording
from movak.operations.base import Operation


@dataclass(slots=True)
class OperationHistory:
    """Track operation history for undo and redo."""

    undo_stack: list[Operation] = field(default_factory=list)
    redo_stack: list[Operation] = field(default_factory=list)

    def apply_operation(self, recording: Recording, operation: Operation) -> None:
        """Apply and record an operation.

        Parameters
        ----------
        recording
            Recording to mutate.
        operation
            Operation to apply.
        """
        operation.apply(recording)
        self.undo_stack.append(operation)
        self.redo_stack.clear()

    def undo(self, recording: Recording) -> None:
        """Undo the most recent operation.

        Parameters
        ----------
        recording
            Recording to mutate.
        """
        if not self.undo_stack:
            raise IndexError("Undo stack is empty.")
        operation = self.undo_stack.pop()
        operation.undo(recording)
        self.redo_stack.append(operation)

    def redo(self, recording: Recording) -> None:
        """Redo the most recently undone operation.

        Parameters
        ----------
        recording
            Recording to mutate.
        """
        if not self.redo_stack:
            raise IndexError("Redo stack is empty.")
        operation = self.redo_stack.pop()
        operation.apply(recording)
        self.undo_stack.append(operation)
