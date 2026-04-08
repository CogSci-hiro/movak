from __future__ import annotations

from PyQt6.QtWidgets import QLabel

from ..components.panel import Panel
from ..style.spacing import Spacing
from ..timeline.timeline_viewport import TimelineViewport
from ..timeline.tracks.spectrogram_track import SpectrogramTrack
from ..timeline.tracks.tier_track import TierTrack
from ..timeline.tracks.waveform_track import WaveformTrack


class TimelinePanel(Panel):
    """Central timeline stack with placeholder spectrogram and tiers."""

    def __init__(self, parent=None) -> None:
        super().__init__("Editor", parent)

        subtitle = QLabel("Timeline, spectrogram, and interval tiers", self)
        subtitle.setObjectName("panelSubtitle")

        self.viewport = TimelineViewport(total_duration=12.0, parent=self)
        self.viewport.add_tracks(
            [
                WaveformTrack(parent=self.viewport),
                SpectrogramTrack(parent=self.viewport),
                TierTrack("Words", parent=self.viewport),
                TierTrack("Phonemes", parent=self.viewport),
            ]
        )

        self.layout.addWidget(subtitle)
        self.layout.addWidget(self.viewport, 1)
        self.layout.addSpacing(Spacing.XS)
