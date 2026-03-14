from __future__ import annotations

from PyQt6.QtGui import QShortcut, QKeySequence


def register_shortcuts(window, controller) -> None:
    """
    Register keyboard shortcuts.
    """

    QShortcut(QKeySequence("S"), window, activated=controller.split_interval)
    QShortcut(QKeySequence("M"), window, activated=controller.merge_interval)

    QShortcut(QKeySequence("Space"), window, activated=controller.toggle_play)

    QShortcut(QKeySequence("Left"), window, activated=controller.move_boundary_left)
    QShortcut(QKeySequence("Right"), window, activated=controller.move_boundary_right)
