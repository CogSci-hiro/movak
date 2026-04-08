from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal

from ..style.palette import Palette


class TimelineWidget(pg.PlotWidget):
    """Interactive placeholder timeline with a visible playhead."""

    clicked = pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("timelineWidget")
        self.setMouseEnabled(x=True, y=False)
        self.showGrid(x=True, y=True, alpha=0.12)
        self.hideButtons()
        self.setMenuEnabled(False)

        self.cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(Palette.CURSOR, width=2))
        self.addItem(self.cursor)

        self.plot(
            [0.0, 0.35, 0.8, 1.25, 1.7, 2.1, 2.55],
            [0.0, 0.22, 0.1, 0.42, 0.18, 0.5, 0.33],
            pen=pg.mkPen(Palette.WAVEFORM, width=2),
        )
        self.setXRange(0.0, 2.8, padding=0.02)
        self.setYRange(-0.1, 0.7, padding=0.05)
        self.cursor.setValue(0.72)

    def mousePressEvent(self, event) -> None:
        position = self.plotItem.vb.mapSceneToView(event.position())
        self.cursor.setValue(position.x())
        self.clicked.emit(position.x())
        super().mousePressEvent(event)
