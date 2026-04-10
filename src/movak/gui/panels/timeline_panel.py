from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..components.panel import Panel
from ..components.transport_bar import TransportBar
from ..style.spacing import Spacing
from ..timeline.timeline_viewport import TimelineViewport
from ..timeline.tracks.spectrogram_track import SpectrogramTrack
from ..timeline.tracks.tier_track import TierTrack
from ..timeline.tracks.waveform_track import WaveformTrack


class TimelinePanel(Panel):
    """Central timeline stack with placeholder spectrogram and tiers."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Editor",
            parent,
            subtitle="Timeline, spectrogram, playback control, and tier editing",
            eyebrow="Session",
        )

        shell = QWidget(self.body)
        shell.setObjectName("trackShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(Spacing.SM)

        self.viewport = TimelineViewport(total_duration=12.0, parent=shell)
        self.waveform_track = WaveformTrack(parent=self.viewport)
        self.spectrogram_track = SpectrogramTrack(parent=self.viewport)
        self.viewport.add_tracks(
            [
                self.waveform_track,
                self.spectrogram_track,
                TierTrack("Words", parent=self.viewport),
                TierTrack("Phonemes", parent=self.viewport),
            ]
        )

        shell_layout.addWidget(self.viewport, 1)

        footer = QLabel(
            "Pinch or mouse wheel zooms. Drag pans horizontally. The bottom scrollbar shifts the visible timeline.",
            shell,
        )
        footer.setObjectName("statCaption")
        shell_layout.addWidget(footer)

        self.transport_bar = TransportBar(parent=self.body)

        self.body_layout.addWidget(shell, 1)
        self.body_layout.addWidget(self.transport_bar)
