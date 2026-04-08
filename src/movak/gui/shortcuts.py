from __future__ import annotations

from PyQt6.QtGui import QShortcut, QKeySequence


def register_shortcuts(window, app_context) -> list[QShortcut]:
    """Register keyboard shortcuts against the application controllers."""

    timeline_controller = app_context.timeline_controller
    playback_controller = app_context.playback_controller

    shortcuts = [
        QShortcut(QKeySequence("S"), window, activated=timeline_controller.split_interval),
        QShortcut(QKeySequence("M"), window, activated=timeline_controller.merge_with_next),
        QShortcut(QKeySequence("Space"), window, activated=playback_controller.toggle_play),
    ]

    window._shortcuts = shortcuts
    return shortcuts
