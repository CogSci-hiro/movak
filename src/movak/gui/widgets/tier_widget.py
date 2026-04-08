from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QGraphicsRectItem

from ..style.palette import Palette


class TierWidget(pg.PlotWidget):
    """Placeholder interval renderer styled like a compact annotation lane."""

    interval_selected = pyqtSignal(str)

    def __init__(self, tier_name: str = "Tier", parent=None) -> None:
        super().__init__(parent=parent)
        self.tier_name = tier_name
        self.setObjectName("tierWidget")
        self.setMouseEnabled(x=True, y=False)
        self.hideAxis("left")
        self.hideButtons()
        self.setMenuEnabled(False)
        self.setYRange(0.0, 1.0, padding=0.0)
        self.setMaximumHeight(88)
        self._draw_placeholder()

    def _draw_placeholder(self) -> None:
        self.clear()
        self.addLine(y=0.08, pen=pg.mkPen(Palette.BORDER, width=1))
        intervals = [
            (0.0, 0.52, f"{self.tier_name} A"),
            (0.52, 1.18, f"{self.tier_name} B"),
            (1.18, 1.92, f"{self.tier_name} C"),
            (1.92, 2.7, f"{self.tier_name} D"),
        ]
        for start, end, label in intervals:
            rect = QGraphicsRectItem(start, 0.18, end - start, 0.54)
            rect.setPen(pg.mkPen(Palette.BORDER, width=1))
            rect.setBrush(pg.mkBrush(Palette.ACCENT_STRONG))
            self.addItem(rect)

            text = pg.TextItem(label, color=Palette.TEXT)
            text.setPos(start + 0.05, 0.34)
            self.addItem(text)

        self.setXRange(0.0, 2.8, padding=0.02)

    def draw_intervals(self) -> None:
        self._draw_placeholder()
