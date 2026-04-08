from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class EventBus(QObject):
    """Singleton Qt event bus used for cross-component communication."""

    recording_loaded = pyqtSignal(str)
    timeline_updated = pyqtSignal()
    cursor_moved = pyqtSignal(float)
    interval_selected = pyqtSignal(str)
    jump_to_time = pyqtSignal(float)

    _instance: "EventBus | None" = None
    _initialized = False

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self.__class__._initialized:
            return
        super().__init__()
        self.__class__._initialized = True


event_bus = EventBus()
