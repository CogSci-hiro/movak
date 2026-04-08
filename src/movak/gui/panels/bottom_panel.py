from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QSplitter, QVBoxLayout

from ..components.panel import Panel
from ..components.rounded_frame import RoundedFrame
from ..style.palette import Palette
from ..style.spacing import Spacing


class BottomPanel(Panel):
    """Bottom diagnostics area with timeline and review lists."""

    def __init__(self, parent=None) -> None:
        super().__init__("Review", parent)

        subtitle = QLabel("Global timeline, issues, and suggestions", self)
        subtitle.setObjectName("panelSubtitle")

        self.global_timeline = pg.PlotWidget(self)
        self.global_timeline.hideButtons()
        self.global_timeline.setMenuEnabled(False)
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

        list_splitter = QSplitter(self)
        list_splitter.setChildrenCollapsible(False)

        errors_frame = RoundedFrame(list_splitter)
        errors_layout = QVBoxLayout(errors_frame)
        errors_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        errors_layout.addWidget(QLabel("Issues", errors_frame))
        errors_layout.addWidget(self.error_list)

        suggestions_frame = RoundedFrame(list_splitter)
        suggestions_layout = QVBoxLayout(suggestions_frame)
        suggestions_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        suggestions_layout.addWidget(QLabel("Suggestions", suggestions_frame))
        suggestions_layout.addWidget(self.suggestion_list)

        content_splitter = QSplitter(self)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.addWidget(self.global_timeline)
        content_splitter.addWidget(list_splitter)
        content_splitter.setSizes([700, 340])

        self.layout.addWidget(subtitle)
        self.layout.addWidget(content_splitter, 1)
