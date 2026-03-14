from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
import pyqtgraph as pg


class TierWidget(pg.PlotWidget):
    """
    Annotation tier renderer.
    """

    interval_selected = pyqtSignal(str)

    def __init__(self, tier_data=None) -> None:
        super().__init__()

        self.tier_data = tier_data

        self.setMouseEnabled(x=True, y=False)

    def draw_intervals(self):
        if self.tier_data is None:
            return
