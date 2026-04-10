from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QPushButton, QWidget


class IconButton(QPushButton):
    """Modern icon-only button with a flat hover treatment."""

    def __init__(
        self,
        icon: QIcon,
        tooltip: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setIcon(icon)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(False)
        self.setFixedSize(34, 34)
        self.setIconSize(QSize(17, 17))
        self.setObjectName("iconButton")
