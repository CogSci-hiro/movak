from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
)
from PyQt6.QtCore import pyqtSignal

from .panels.left_panel import LeftPanel
from .panels.timeline_panel import TimelinePanel
from .panels.right_panel import RightPanel
from .panels.bottom_panel import BottomPanel


class MainWindow(QMainWindow):
    """
    Main application window.

    Responsibilities
    ----------------
    * create panel layout
    * manage application state
    * coordinate controllers
    * load recordings
    """

    recording_loaded = pyqtSignal(str)

    def __init__(self, controller=None) -> None:
        super().__init__()

        self.controller = controller

        self.setWindowTitle("Movak")

        self._build_ui()

    def _build_ui(self) -> None:
        self._create_toolbar()

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        middle_layout = QHBoxLayout()

        self.left_panel = LeftPanel()
        self.timeline_panel = TimelinePanel()
        self.right_panel = RightPanel()

        middle_layout.addWidget(self.left_panel, 1)
        middle_layout.addWidget(self.timeline_panel, 4)
        middle_layout.addWidget(self.right_panel, 2)

        self.bottom_panel = BottomPanel()

        main_layout.addLayout(middle_layout)
        main_layout.addWidget(self.bottom_panel, 1)

        self._connect_signals()

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Playback")
        self.addToolBar(toolbar)

    def _connect_signals(self) -> None:
        self.left_panel.recording_selected.connect(self._on_recording_selected)

    def _on_recording_selected(self, recording_id: str) -> None:
        if self.controller:
            self.controller.load_recording(recording_id)

        self.recording_loaded.emit(recording_id)
