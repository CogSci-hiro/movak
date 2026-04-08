from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QProgressBar, QVBoxLayout, QWidget

from ..components.panel import Panel
from ..components.modern_splitter import ModernSplitter
from ..style.palette import Palette
from ..style.spacing import Spacing


class BottomPanel(Panel):
    """Bottom diagnostics area with timeline and review lists."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Review",
            parent,
            subtitle="Session overview, flagged issues, and suggested actions",
            eyebrow="Operations",
        )

        stats = QWidget(self.body)
        stats_layout = QVBoxLayout(stats)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(Spacing.SM)

        overview = QWidget(stats)
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(Spacing.SM)

        overview_title = QLabel("Review Progress", overview)
        overview_title.setObjectName("sectionLabel")
        overview_text = QLabel("12 flagged regions across 3 recordings", overview)
        overview_text.setObjectName("statCaption")
        progress = QProgressBar(overview)
        progress.setRange(0, 100)
        progress.setValue(58)
        progress.setTextVisible(False)
        overview_layout.addWidget(overview_title)
        overview_layout.addWidget(overview_text)
        overview_layout.addWidget(progress)

        self.global_timeline = pg.PlotWidget(self.body)
        self.global_timeline.hideButtons()
        self.global_timeline.setMenuEnabled(False)
        self.global_timeline.setBackground(Palette.PANEL)
        self.global_timeline.plot(
            [0.0, 0.4, 0.7, 1.1, 1.6, 2.1, 2.7],
            [0.1, 0.35, 0.22, 0.5, 0.3, 0.55, 0.42],
            pen=pg.mkPen(Palette.WAVEFORM, width=2),
        )

        self.error_list = QListWidget(self)
        self.suggestion_list = QListWidget(self)

        for text in ("Boundary confidence low", "Missing label review", "Potential overlap detected"):
            QListWidgetItem(text, self.error_list)
        for text in ("Accept phone split", "Merge duplicated silence", "Normalize speaker tier"):
            QListWidgetItem(text, self.suggestion_list)

        list_splitter = ModernSplitter(Qt.Orientation.Horizontal, self.body)
        list_splitter.setChildrenCollapsible(False)

        errors_frame = QWidget(list_splitter)
        errors_layout = QVBoxLayout(errors_frame)
        errors_layout.setContentsMargins(0, 0, 0, 0)
        errors_layout.addWidget(QLabel("Issues", errors_frame))
        errors_layout.addWidget(self.error_list)

        suggestions_frame = QWidget(list_splitter)
        suggestions_layout = QVBoxLayout(suggestions_frame)
        suggestions_layout.setContentsMargins(0, 0, 0, 0)
        suggestions_layout.addWidget(QLabel("Suggestions", suggestions_frame))
        suggestions_layout.addWidget(self.suggestion_list)

        timeline_frame = QWidget(self.body)
        timeline_layout = QVBoxLayout(timeline_frame)
        timeline_layout.setContentsMargins(0, Spacing.SM, 0, 0)
        timeline_layout.setSpacing(Spacing.SM)
        timeline_layout.addWidget(QLabel("Activity Sweep", timeline_frame))
        timeline_layout.addWidget(self.global_timeline, 1)

        content_splitter = ModernSplitter(Qt.Orientation.Horizontal, self.body)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.addWidget(timeline_frame)
        content_splitter.addWidget(list_splitter)
        content_splitter.setSizes([700, 340])

        stats_layout.addWidget(overview)

        self.body_layout.addWidget(stats)
        self.body_layout.addWidget(content_splitter, 1)
