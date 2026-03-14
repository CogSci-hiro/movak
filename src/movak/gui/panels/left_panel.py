from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeView
from PyQt6.QtCore import pyqtSignal


class LeftPanel(QWidget):
    """
    Corpus navigation panel.
    """

    recording_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tree = QTreeView()

        layout.addWidget(self.tree)

        self.tree.clicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, index) -> None:
        recording_id = str(index.data())
        self.recording_selected.emit(recording_id)
