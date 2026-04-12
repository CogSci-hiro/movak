from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ...features.analysis_inspector import AnalysisSnapshot
from ..components.panel import Panel
from ..components.modern_splitter import ModernSplitter
from ..style.spacing import Spacing
from ..widgets.analysis_plot_widgets import FormantSpacePlotWidget, PsdPlotWidget


class RightPanel(Panel):
    """Cursor-centered analysis inspector for the active audio file."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Analysis",
            parent,
            subtitle="Formant space and power spectral density around the current cursor",
            eyebrow="Inspector",
        )

        summary_label = QLabel(
            "The plots below use a short analysis window centered on the current cursor/playhead position.",
            self.body,
        )
        summary_label.setWordWrap(True)
        summary_label.setObjectName("statCaption")

        self.placeholder_label = QLabel(self.body)
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.placeholder_label.setObjectName("emptyStateText")

        self.formant_plot_widget = FormantSpacePlotWidget(self.body)
        self.psd_plot_widget = PsdPlotWidget(self.body)

        self.plot_splitter = ModernSplitter(Qt.Orientation.Vertical, self.body)
        self.plot_splitter.addWidget(self.formant_plot_widget)
        self.plot_splitter.addWidget(self.psd_plot_widget)
        self.plot_splitter.setStretchFactor(0, 1)
        self.plot_splitter.setStretchFactor(1, 1)
        self.plot_splitter.setSizes([280, 280])

        self.body_layout.addWidget(summary_label)
        self.body_layout.addWidget(self.placeholder_label)
        self.body_layout.addWidget(self.plot_splitter, 1)

        self.show_placeholder_state("Load audio to inspect formants and PSD around the cursor.")

    def set_analysis_snapshot(self, snapshot: AnalysisSnapshot) -> None:
        """Render the latest cursor-centered analysis results."""

        self.placeholder_label.setVisible(False)
        if snapshot.channel_formants:
            self.formant_plot_widget.set_formant_points(
                snapshot.channel_formants,
                snapshot.channel_formant_confidences,
            )
        else:
            self.formant_plot_widget.set_formant_point(snapshot.formant, snapshot.formant_confidence)
        self.psd_plot_widget.set_psd(snapshot.psd, snapshot.formant_frequencies_hz)

    def show_placeholder_state(self, message: str) -> None:
        """Show a lightweight empty state while keeping the plots stable."""

        self.placeholder_label.setText(message)
        self.placeholder_label.setVisible(True)
        self.formant_plot_widget.clear_plot()
        self.psd_plot_widget.clear_plot()
        self.formant_plot_widget.set_state_message(message)
        self.psd_plot_widget.set_state_message(message)


class InspectorDetailPane(Panel):
    """Compact inspector/details pane for right-side tool windows."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Inspector",
            parent,
            subtitle="Focused selection details and quick diagnostics",
            eyebrow="Details",
        )

        detail_block = QWidget(self.body)
        detail_layout = QFormLayout(detail_block)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(Spacing.SM)

        fields = (
            ("Recording", "recording_001"),
            ("Speaker", "Speaker A"),
            ("Tier", "Words"),
            ("Start", "01.75s"),
            ("End", "03.10s"),
            ("Confidence", "0.984"),
        )
        for label, value in fields:
            key_label = QLabel(label, detail_block)
            key_label.setObjectName("sectionLabel")
            value_label = QLabel(value, detail_block)
            detail_layout.addRow(key_label, value_label)

        note_title = QLabel("Recent Notes", self.body)
        note_title.setObjectName("sectionLabel")

        notes = QListWidget(self.body)
        for text in (
            "Embedding cluster matches prior token family",
            "Boundary candidate retained after smoothing",
            "No overlap with adjacent annotation",
        ):
            QListWidgetItem(text, notes)

        self.body_layout.addWidget(detail_block)
        self.body_layout.addWidget(note_title)
        self.body_layout.addWidget(notes, 1)
