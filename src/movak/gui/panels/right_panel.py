from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtWidgets import QLabel

from ..components.panel import Panel
from ..style.palette import Palette


class RightPanel(Panel):
    """Visualization placeholder area."""

    def __init__(self, parent=None) -> None:
        super().__init__("Analysis", parent)

        subtitle = QLabel("Embedding and token distribution views", self)
        subtitle.setObjectName("panelSubtitle")

        self.plot_widget = pg.PlotWidget(self)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.hideButtons()
        self.plot_widget.setMenuEnabled(False)

        scatter = pg.ScatterPlotItem(
            x=[0.1, 0.45, 0.9, 1.2, 1.55],
            y=[1.2, 0.5, 1.5, 0.85, 1.1],
            size=10,
            brush=pg.mkBrush(Palette.ACCENT),
            pen=pg.mkPen(Palette.ACCENT_STRONG, width=1.0),
        )
        self.plot_widget.addItem(scatter)

        self.layout.addWidget(subtitle)
        self.layout.addWidget(self.plot_widget, 1)
