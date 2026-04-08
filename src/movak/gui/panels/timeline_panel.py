from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QProgressBar, QStyle, QVBoxLayout, QWidget

from ..components.panel import Panel
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

        transport = QWidget(self.body)
        transport_layout = QHBoxLayout(transport)
        transport_layout.setContentsMargins(0, 0, 0, 0)
        transport_layout.setSpacing(Spacing.SM)

        current_state = QLabel("REC 01  •  Speaker A", transport)
        current_state.setObjectName("sectionLabel")
        transport_progress = QProgressBar(transport)
        transport_progress.setRange(0, 100)
        transport_progress.setValue(62)
        transport_progress.setTextVisible(False)

        focus_button = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward), "Focus Region", transport)
        focus_button.setObjectName("ghostButton")
        analyze_button = QPushButton("Run Pass", transport)
        analyze_button.setObjectName("primaryButton")

        transport_layout.addWidget(current_state)
        transport_layout.addWidget(transport_progress, 1)
        transport_layout.addWidget(focus_button)
        transport_layout.addWidget(analyze_button)

        shell = QWidget(self.body)
        shell.setObjectName("trackShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, Spacing.SM, 0, 0)
        shell_layout.setSpacing(Spacing.SM)

        self.viewport = TimelineViewport(total_duration=12.0, parent=shell)
        self.viewport.add_tracks(
            [
                WaveformTrack(parent=self.viewport),
                SpectrogramTrack(parent=self.viewport),
                TierTrack("Words", parent=self.viewport),
                TierTrack("Phonemes", parent=self.viewport),
            ]
        )

        shell_layout.addWidget(self.viewport, 1)

        footer = QLabel(
            "Shift + mouse wheel pans horizontally. Mouse wheel zooms the shared timeline.",
            shell,
        )
        footer.setObjectName("statCaption")
        shell_layout.addWidget(footer)

        self.body_layout.addWidget(transport)
        self.body_layout.addWidget(shell, 1)
        self.body_layout.addSpacing(Spacing.XS)
