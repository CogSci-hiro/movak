from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .event_bus import EventBus, event_bus


@dataclass(slots=True)
class AppContext:
    """Central dependency container for the GUI layer."""

    model: Any = None
    controllers: dict[str, Any] = field(default_factory=dict)
    event_bus: EventBus = field(default_factory=lambda: event_bus)
    playback_controller: Any = None
    navigation_controller: Any = None
