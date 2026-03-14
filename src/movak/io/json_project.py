"""JSON project I/O placeholders."""

from __future__ import annotations


class JsonProjectIO:
    """Read and write Movak project files."""

    def load(self, path: str) -> None:
        """Load a project file.

        Parameters
        ----------
        path
            Input file path.
        """
        pass

    def save(self, path: str) -> None:
        """Save a project file.

        Parameters
        ----------
        path
            Output file path.
        """
        pass
