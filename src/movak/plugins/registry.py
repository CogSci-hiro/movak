"""Plugin registry placeholders."""

from __future__ import annotations

from movak.plugins.api import Plugin


class PluginRegistry:
    """Register and retrieve plugins."""

    def register(self, plugin: Plugin) -> None:
        """Register a plugin.

        Parameters
        ----------
        plugin
            Plugin instance.
        """
        pass

    def list_plugins(self) -> list[Plugin]:
        """List registered plugins.

        Returns
        -------
        list[Plugin]
            Registered plugins.
        """
        pass
