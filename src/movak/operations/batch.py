"""Batch operations."""

from __future__ import annotations

from dataclasses import dataclass, field

from movak.core.recording import Recording
from movak.operations.base import Operation


@dataclass(slots=True)
class BatchReplaceOperation(Operation):
    """Apply a collection of operations as a unit."""

    operations: list[Operation] = field(default_factory=list)

    def apply(self, recording: Recording) -> None:
        """Apply the operation batch."""
        applied_operations: list[Operation] = []
        try:
            for operation in self.operations:
                operation.apply(recording)
                applied_operations.append(operation)
        except Exception:
            for operation in reversed(applied_operations):
                operation.undo(recording)
            raise

    def undo(self, recording: Recording) -> None:
        """Undo the operation batch."""
        for operation in reversed(self.operations):
            operation.undo(recording)
