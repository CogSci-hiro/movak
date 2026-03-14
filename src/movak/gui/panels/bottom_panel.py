from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QListWidget
import pyqtgraph as pg


class BottomPanel(QWidget):
    """
    Bottom diagnostics panel.
    """

    def __init__(self) -> None:
        super().__init__()

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.global_timeline = pg.PlotWidget()
        self.error_list = QListWidget()
        self.suggestions = QListWidget()

        layout.addWidget(self.global_timeline, 3)
        layout.addWidget(self.error_list, 1)
        layout.addWidget(self.suggestions, 1)
