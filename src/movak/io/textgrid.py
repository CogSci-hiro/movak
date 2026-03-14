"""TextGrid I/O placeholders."""

from __future__ import annotations


class TextGridIO:
    """Read and write TextGrid-style annotation files."""

    def load(self, path: str) -> None:
        """Load annotations from a TextGrid file.

        Parameters
        ----------
        path
            Input file path.
        """
        pass

    def save(self, path: str) -> None:
        """Save annotations to a TextGrid file.

        Parameters
        ----------
        path
            Output file path.
        """
        pass
