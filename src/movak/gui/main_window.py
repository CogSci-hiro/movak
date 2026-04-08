from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from .app_context import AppContext
from .components.frameless_window import FramelessWindow
from .components.modern_splitter import ModernSplitter
from .components.toolbar import Toolbar
from .components.title_bar import TitleBar
from .panels.bottom_panel import BottomPanel
from .panels.left_panel import LeftPanel
from .panels.right_panel import RightPanel
from .panels.timeline_panel import TimelinePanel
from .style.spacing import Spacing
from .style.theme import apply_theme


class MainWindow(FramelessWindow):
    """Main IDE-like window composed from thin GUI placeholders."""

    def __init__(self, app_context: AppContext | None = None) -> None:
        super().__init__()
        self.app_context = app_context or AppContext()

        app = QApplication.instance()
        if app is not None:
            apply_theme(app)

        self.setWindowTitle("Movak")
        self.resize(1600, 980)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("root")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(0)

        self.window_frame = QWidget(root)
        self.window_frame.setObjectName("windowFrame")
        frame_layout = QVBoxLayout(self.window_frame)
        frame_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        frame_layout.setSpacing(Spacing.MD)

        self.toolbar = Toolbar(self.window_frame)
        self.toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.title_bar = TitleBar(self.toolbar, self.window_frame)
        self.set_title_bar(self.title_bar)

        self.left_panel = LeftPanel(self.window_frame)
        self.timeline_panel = TimelinePanel(self.window_frame)
        self.right_panel = RightPanel(self.window_frame)
        self.bottom_panel = BottomPanel(self.window_frame)

        horizontal_splitter = ModernSplitter(Qt.Orientation.Horizontal, self.window_frame)
        horizontal_splitter.addWidget(self.left_panel)
        horizontal_splitter.addWidget(self.timeline_panel)
        horizontal_splitter.addWidget(self.right_panel)
        horizontal_splitter.setStretchFactor(0, 2)
        horizontal_splitter.setStretchFactor(1, 7)
        horizontal_splitter.setStretchFactor(2, 3)
        horizontal_splitter.setSizes([280, 860, 360])

        vertical_splitter = ModernSplitter(Qt.Orientation.Vertical, self.window_frame)
        vertical_splitter.addWidget(horizontal_splitter)
        vertical_splitter.addWidget(self.bottom_panel)
        vertical_splitter.setStretchFactor(0, 7)
        vertical_splitter.setStretchFactor(1, 3)
        vertical_splitter.setSizes([700, 240])

        frame_layout.addWidget(self.title_bar)
        frame_layout.addWidget(vertical_splitter, 1)
        layout.addWidget(self.window_frame, 1)
