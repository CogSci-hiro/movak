from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtWidgets import QFormLayout, QGridLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ..components.panel import Panel
from ..style.palette import Palette
from ..style.spacing import Spacing


class RightPanel(Panel):
    """Visualization placeholder area."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Analysis",
            parent,
            subtitle="Embeddings, confidence metrics, and token distribution",
            eyebrow="Inspector",
        )

        metrics = QWidget(self.body)
        metrics_layout = QGridLayout(metrics)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setHorizontalSpacing(Spacing.SM)
        metrics_layout.setVerticalSpacing(Spacing.SM)

        for index, (value, label) in enumerate(
            (
                ("98.4%", "Alignment"),
                ("12", "Flags"),
                ("4.2h", "Reviewed"),
                ("18", "Pending"),
            )
        ):
            card = QWidget(metrics)
            card.setObjectName("metricCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
            card_layout.setSpacing(Spacing.XXS)

            value_label = QLabel(value, card)
            value_label.setObjectName("metricValue")
            text_label = QLabel(label, card)
            text_label.setObjectName("metricLabel")

            card_layout.addWidget(value_label)
            card_layout.addWidget(text_label)
            metrics_layout.addWidget(card, index // 2, index % 2)

        plot_frame = QWidget(self.body)
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(0, Spacing.SM, 0, 0)
        plot_layout.setSpacing(Spacing.SM)

        plot_label = QLabel("Embedding Projection", plot_frame)
        plot_label.setObjectName("sectionLabel")

        self.plot_widget = pg.PlotWidget(plot_frame)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.hideButtons()
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setBackground(Palette.PANEL)
        self.plot_widget.getPlotItem().getAxis("bottom").setPen(pg.mkPen(Palette.TEXT_DIM))
        self.plot_widget.getPlotItem().getAxis("left").setPen(pg.mkPen(Palette.TEXT_DIM))
        self.plot_widget.getPlotItem().getAxis("bottom").setTextPen(pg.mkPen(Palette.TEXT_MUTED))
        self.plot_widget.getPlotItem().getAxis("left").setTextPen(pg.mkPen(Palette.TEXT_MUTED))

        scatter = pg.ScatterPlotItem(
            x=[0.1, 0.45, 0.9, 1.2, 1.55],
            y=[1.2, 0.5, 1.5, 0.85, 1.1],
            size=12,
            brush=pg.mkBrush(Palette.ACCENT),
            pen=pg.mkPen(Palette.ACCENT_VIOLET, width=1.2),
        )
        self.plot_widget.addItem(scatter)

        plot_layout.addWidget(plot_label)
        plot_layout.addWidget(self.plot_widget, 1)

        status_frame = QWidget(self.body)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(0, Spacing.SM, 0, 0)
        status_layout.setSpacing(Spacing.XS)
        status_title = QLabel("Model Status", status_frame)
        status_title.setObjectName("sectionLabel")
        status_copy = QLabel(
            "Confidence overlays and embedding panels are ready. Select an interval to reveal detailed diagnostics here.",
            status_frame,
        )
        status_copy.setWordWrap(True)
        status_copy.setObjectName("emptyStateText")
        status_layout.addWidget(status_title)
        status_layout.addWidget(status_copy)

        self.body_layout.addWidget(metrics)
        self.body_layout.addWidget(plot_frame, 1)
        self.body_layout.addWidget(status_frame)


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
