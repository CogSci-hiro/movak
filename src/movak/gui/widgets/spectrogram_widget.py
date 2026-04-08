from __future__ import annotations

import numpy as np
import pyqtgraph as pg


class SpectrogramWidget(pg.PlotWidget):
    """Spectrogram placeholder widget."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("spectrogramWidget")
        self.hideButtons()
        self.setMenuEnabled(False)
        self.hideAxis("left")

        self.image = pg.ImageItem()
        self.addItem(self.image)
        self.set_spectrogram(self._build_placeholder())

    def _build_placeholder(self) -> np.ndarray:
        x = np.linspace(0.0, 1.0, 256)
        y = np.linspace(0.0, 1.0, 96)
        xx, yy = np.meshgrid(x, y)
        return np.sin(xx * 20.0) * 0.35 + np.cos(yy * 28.0) * 0.25 + xx * 0.4

    def set_spectrogram(self, spec: np.ndarray) -> None:
        self.image.setImage(spec)
