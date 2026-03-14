from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from ..widgets.timeline_widget import TimelineWidget
from ..widgets.spectrogram_widget import SpectrogramWidget
from ..widgets.tier_widget import TierWidget


class TimelinePanel(QWidget):
    """
    Main timeline view panel.
    """

    def __init__(self, controller=None) -> None:
        super().__init__()

        self.controller = controller

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.timeline = TimelineWidget()
        self.spectrogram = SpectrogramWidget()

        layout.addWidget(self.spectrogram, 2)
        layout.addWidget(self.timeline, 3)

        self.tiers = []

    def add_tier(self, tier_data) -> None:
        tier = TierWidget(tier_data)
        self.layout().addWidget(tier)
        self.tiers.append(tier)
