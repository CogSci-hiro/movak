"""Plugin API placeholders."""

from __future__ import annotations


class Plugin:
    """Base plugin contract."""

    def activate(self) -> None:
        """Activate the plugin."""
        pass

    def deactivate(self) -> None:
        """Deactivate the plugin."""
        pass
