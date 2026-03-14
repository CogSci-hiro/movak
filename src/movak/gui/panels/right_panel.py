from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg


class RightPanel(QWidget):
    """
    Visualization panel for token-level plots.
    """

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.plot_widget = pg.PlotWidget()

        layout.addWidget(self.plot_widget)

        self.scatter = pg.ScatterPlotItem()

        self.plot_widget.addItem(self.scatter)

        self.scatter.sigClicked.connect(self._on_point_clicked)

    def set_data(self, x, y, token_ids):
        spots = [
            {"pos": (xi, yi), "data": token_id}
            for xi, yi, token_id in zip(x, y, token_ids)
        ]

        self.scatter.setData(spots)

    def _on_point_clicked(self, plot, points):
        token_id = points[0].data()

        # should emit signal in full implementation
        print("Jump to token:", token_id)
