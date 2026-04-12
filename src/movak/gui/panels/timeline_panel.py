from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...annotations import build_demo_annotation_document
from ..controllers.annotation_editor_controller import AnnotationEditorController, AnnotationSelection
from ..components.panel import Panel
from ..components.transport_bar import TransportBar
from ..style.spacing import Spacing
from ..timeline.timeline_viewport import TimelineViewport
from ..timeline.tracks.spectrogram_track import SpectrogramTrack
from ..timeline.tracks.tier_track import build_tracks
from ..timeline.tracks.waveform_track import WaveformTrack


class TimelinePanel(Panel):
    """Central timeline stack with waveform, spectrogram, and editable annotation tiers."""

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
        self.annotation_document = build_demo_annotation_document(self.viewport.total_duration)
        self.annotation_controller = AnnotationEditorController(self.annotation_document, parent=self)
        self.annotation_tracks = build_tracks(self.annotation_document.tiers, self.annotation_controller, parent=self.viewport)
        self.viewport.add_tracks(
            [
                self.waveform_track,
                self.spectrogram_track,
                *self.annotation_tracks,
            ]
        )
        self.spectrogram_track.point_selected.connect(self._handle_spectrogram_point_selected)
        self.spectrogram_track.region_selected.connect(self._handle_spectrogram_region_selected)
        self.annotation_controller.selection_changed.connect(self._handle_annotation_selection_changed)
        self.viewport.time_selected.connect(self._handle_time_selected)

        shell_layout.addWidget(self.viewport, 1)

        footer = QLabel(
            "Mouse wheel or pinch zooms. Click empty annotation space to move the cursor. On annotation tiers: drag interval edges or bodies, drag points horizontally, type to edit the selected label, use Backspace to erase characters, Delete to remove annotations, Enter to relabel in a dialog, I/P to create, S to split, and M to merge.",
            shell,
        )
        footer.setObjectName("statCaption")
        shell_layout.addWidget(footer)

        self.selection_status_label = QLabel("Selection: none", shell)
        self.selection_status_label.setObjectName("statCaption")
        shell_layout.addWidget(self.selection_status_label)

        self.transport_bar = TransportBar(parent=self.body)

        self.body_layout.addWidget(shell, 1)
        self.body_layout.addWidget(self.transport_bar)

    def _handle_spectrogram_point_selected(self, time_seconds: float, frequency_hz: float) -> None:
        self.viewport.time_axis.set_selected_time(time_seconds)
        self.selection_status_label.setText(
            f"Point: time {time_seconds:.3f}s, frequency {frequency_hz:.0f} Hz"
        )

    def _handle_spectrogram_region_selected(
        self,
        start_time_seconds: float,
        end_time_seconds: float,
        low_frequency_hz: float,
        high_frequency_hz: float,
    ) -> None:
        self.viewport.time_axis.set_selected_time(None)
        self.selection_status_label.setText(
            "Region: "
            f"{start_time_seconds:.3f}-{end_time_seconds:.3f}s, "
            f"{low_frequency_hz:.0f}-{high_frequency_hz:.0f} Hz"
        )

    def _handle_annotation_selection_changed(self, selection: AnnotationSelection) -> None:
        if selection.tier_id is None:
            self.selection_status_label.setText("Selection: none")
            return

        tier = self.annotation_document.get_tier(selection.tier_id)
        if selection.annotation_id is None:
            self.selection_status_label.setText(f"Active tier: {tier.name} ({tier.tier_type})")
            return

        annotation = self.annotation_document.find_annotation(selection.tier_id, selection.annotation_id)
        if annotation is None:
            self.selection_status_label.setText("Selection: none")
            return
        if hasattr(annotation, "start_time") and hasattr(annotation, "end_time"):
            self.selection_status_label.setText(
                f"{tier.name}: {annotation.start_time:.3f}-{annotation.end_time:.3f}s  '{annotation.text}'"
            )
            return
        self.selection_status_label.setText(f"{tier.name}: {annotation.time:.3f}s  '{annotation.text}'")

    def _handle_time_selected(self, time_seconds: float) -> None:
        self.viewport.time_axis.set_selected_time(time_seconds)
