from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal


class TimelineWidget(pg.PlotWidget):
    """
    Timeline rendering widget using pyqtgraph.

    Handles:
    * zoom
    * scroll
    * cursor display
    """

    clicked = pyqtSignal(float)

    def __init__(self) -> None:
        super().__init__()

        self.setMouseEnabled(x=True, y=False)

        self.cursor = pg.InfiniteLine(angle=90, movable=False)

        self.addItem(self.cursor)

    def mousePressEvent(self, event):
        pos = self.plotItem.vb.mapSceneToView(event.position())
        self.clicked.emit(pos.x())
        super().mousePressEvent(event)
