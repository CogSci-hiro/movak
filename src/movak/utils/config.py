"""Configuration utility placeholders."""

from __future__ import annotations


class Config:
    """Application configuration container."""

    def load(self) -> None:
        """Load configuration values."""
        pass

    def save(self) -> None:
        """Persist configuration values."""
        pass
