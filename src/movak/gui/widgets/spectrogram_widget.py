from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget
import numpy as np


class SpectrogramWidget(pg.PlotWidget):
    """
    Spectrogram display widget.
    """

    def __init__(self) -> None:
        super().__init__()

        self.image = pg.ImageItem()

        self.addItem(self.image)

    def set_spectrogram(self, spec: np.ndarray) -> None:
        self.image.setImage(spec)
