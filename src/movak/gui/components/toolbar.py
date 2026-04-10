from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QStyle, QWidget

from ..style.spacing import Spacing
from .icon_button import IconButton


class Toolbar(QWidget):
    """Minimal icon-only action strip used inside the custom title bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbarStrip")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.mode_label = QLabel("Session", self)
        self.mode_label.setObjectName("windowSubtitle")
        style = self.style()
        self.open_button = IconButton(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Open", self)
        self.save_button = IconButton(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save", self)
        self.render_button = IconButton(style.standardIcon(QStyle.StandardPixmap.SP_CommandLink), "Run analysis", self)

        layout.addWidget(self.mode_label)
        layout.addSpacing(Spacing.SM)
        layout.addWidget(self.open_button)
        layout.addWidget(self.save_button)
        layout.addSpacing(Spacing.SM)
        layout.addWidget(self.render_button)
