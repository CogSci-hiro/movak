from __future__ import annotations

from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QLineEdit, QTreeView, QVBoxLayout, QWidget

from ..components.panel import Panel
from ..style.spacing import Spacing


class LeftPanel(Panel):
    """Corpus browser pane shown inside the left dock."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Corpus",
            parent,
            subtitle="Recordings, annotation sets, and active corpus context",
            eyebrow="Project",
        )

        corpus_section = QWidget(self.body)
        corpus_layout = QVBoxLayout(corpus_section)
        corpus_layout.setContentsMargins(0, 0, 0, 0)
        corpus_layout.setSpacing(Spacing.SM)

        corpus_label = QLabel("Active Corpus", corpus_section)
        corpus_label.setObjectName("sectionLabel")
        detail_label = QLabel("3 recordings loaded   2 flagged for review", corpus_section)
        detail_label.setObjectName("statCaption")

        self.tree = QTreeView(corpus_section)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setRootIsDecorated(True)

        model = QStandardItemModel(self.tree)
        root = model.invisibleRootItem()
        corpus = QStandardItem("Demo Corpus")
        corpus.appendRow(QStandardItem("recording_001"))
        corpus.appendRow(QStandardItem("recording_002"))
        corpus.appendRow(QStandardItem("recording_003"))
        root.appendRow(corpus)
        self.tree.setModel(model)
        self.tree.expandAll()

        corpus_layout.addWidget(corpus_label)
        corpus_layout.addWidget(detail_label)
        corpus_layout.addWidget(self.tree, 1)

        helper = QLabel(
            "Select a recording to reveal interval tools and review details.",
            self.body,
        )
        helper.setObjectName("emptyStateText")
        helper.setWordWrap(True)

        self.body_layout.addWidget(corpus_section, 1)
        self.body_layout.addWidget(helper)


class ReviewQueuePane(Panel):
    """Review queue pane for flagged items."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Review Queue",
            parent,
            subtitle="Open issues, low-confidence regions, and suggested follow-up",
            eyebrow="Review",
        )

        issue_list = QListWidget(self.body)
        for text in (
            "Boundary confidence low",
            "Missing label review",
            "Potential overlap detected",
            "Speaker handoff needs validation",
        ):
            QListWidgetItem(text, issue_list)

        helper = QLabel("Select a flagged issue to jump the editor to the relevant region.", self.body)
        helper.setObjectName("emptyStateText")
        helper.setWordWrap(True)

        self.body_layout.addWidget(issue_list, 1)
        self.body_layout.addWidget(helper)


class SearchPane(Panel):
    """Search pane for quick corpus filtering."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Search",
            parent,
            subtitle="Filter tokens, labels, and annotations across the active corpus",
            eyebrow="Query",
        )

        search_input = QLineEdit(self.body)
        search_input.setPlaceholderText("Search labels, speakers, or notes")

        result_list = QListWidget(self.body)
        for text in ("hello", "world", "today", "speaker_a", "pause"):
            QListWidgetItem(text, result_list)

        helper = QLabel("Results update within the active project scope.", self.body)
        helper.setObjectName("emptyStateText")

        self.body_layout.addWidget(search_input)
        self.body_layout.addWidget(result_list, 1)
        self.body_layout.addWidget(helper)


class ExportPane(Panel):
    """Export pane for quick output tasks."""

    def __init__(self, parent=None) -> None:
        super().__init__(
            "Exports",
            parent,
            subtitle="Common output actions and batch export presets",
            eyebrow="Output",
        )

        export_list = QListWidget(self.body)
        for text in (
            "Export TextGrid package",
            "Render review CSV",
            "Create token summary JSON",
            "Batch audio snippets",
        ):
            QListWidgetItem(text, export_list)

        helper = QLabel("Choose an export target to configure options in the main workspace.", self.body)
        helper.setObjectName("emptyStateText")
        helper.setWordWrap(True)

        self.body_layout.addWidget(export_list, 1)
        self.body_layout.addWidget(helper)
