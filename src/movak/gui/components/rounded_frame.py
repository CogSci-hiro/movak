from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QWidget


class RoundedFrame(QFrame):
    """Rounded frame with an optional subtle shadow for depth."""

    def __init__(self, parent: QWidget | None = None, *, shadow: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("roundedFrame")
        if shadow:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(24)
            effect.setOffset(0, 8)
            effect.setColor(QColor(0, 0, 0, 90))
            self.setGraphicsEffect(effect)
