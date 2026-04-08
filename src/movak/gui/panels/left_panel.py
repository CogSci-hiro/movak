from __future__ import annotations

from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QLabel, QTreeView

from ..components.panel import Panel


class LeftPanel(Panel):
    """Corpus navigation placeholder panel."""

    def __init__(self, parent=None) -> None:
        super().__init__("Corpus", parent)

        subtitle = QLabel("Recordings and annotation sets", self)
        subtitle.setObjectName("panelSubtitle")

        self.tree = QTreeView(self)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(False)

        model = QStandardItemModel(self.tree)
        root = model.invisibleRootItem()
        corpus = QStandardItem("Demo Corpus")
        corpus.appendRow(QStandardItem("recording_001"))
        corpus.appendRow(QStandardItem("recording_002"))
        corpus.appendRow(QStandardItem("recording_003"))
        root.appendRow(corpus)
        self.tree.setModel(model)
        self.tree.expandAll()

        self.layout.addWidget(subtitle)
        self.layout.addWidget(self.tree, 1)
