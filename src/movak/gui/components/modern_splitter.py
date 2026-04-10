from __future__ import annotations

from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QSplitterHandle, QWidget

from ..style.palette import Palette


class _SplitterHandle(QSplitterHandle):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        if self.orientation() == Qt.Orientation.Horizontal:
            rect = self.rect().adjusted(4, 18, -4, -18)
        else:
            rect = self.rect().adjusted(18, 4, -18, -4)

        if self.underMouse():
            glow = QColor(Palette.TEXT_MUTED)
            glow.setAlpha(24)
            painter.setBrush(glow)
            painter.drawRoundedRect(rect, 1.5, 1.5)
        painter.end()
        super().paintEvent(event)


class ModernSplitter(QSplitter):
    """QSplitter tuned for subtle IDE-like resizing affordances."""

    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None = None) -> None:
        super().__init__(orientation, parent)
        self.setChildrenCollapsible(False)
        self.setHandleWidth(8)
        self.setOpaqueResize(True)

    def createHandle(self) -> QSplitterHandle:
        return _SplitterHandle(self.orientation(), self)
