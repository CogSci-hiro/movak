from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QStyle, QVBoxLayout, QWidget

from .app_context import AppContext
from .components.left_dock import LeftDock, LeftPaneSpec
from .components.macos_window import apply_integrated_macos_chrome
from .components.modern_splitter import ModernSplitter
from .components.right_dock import RightDock, RightPaneSpec
from .panels.bottom_panel import BottomPanel
from .panels.left_panel import ExportPane, LeftPanel, ReviewQueuePane, SearchPane
from .panels.right_panel import InspectorDetailPane, RightPanel
from .panels.timeline_panel import TimelinePanel
from .style.spacing import Spacing
from .style.theme import apply_theme


class MainWindow(QMainWindow):
    """Main IDE-like window composed from thin GUI placeholders."""

    def __init__(self, app_context: AppContext | None = None) -> None:
        super().__init__()
        self.app_context = app_context or AppContext()
        self._active_left_pane_id: str | None = "corpus"
        self._active_right_pane_id: str | None = "analysis"
        self._macos_chrome_applied = False

        app = QApplication.instance()
        if app is not None:
            apply_theme(app)

        self.setWindowTitle("Movak")
        self.setMinimumSize(960, 640)
        self.resize(1600, 980)
        self._configure_native_chrome()
        self._build_ui()

    def _configure_native_chrome(self) -> None:
        if sys.platform == "darwin":
            self.setUnifiedTitleAndToolBarOnMac(True)
            self.setWindowTitle("")

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("root")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        if sys.platform == "darwin":
            layout.setContentsMargins(Spacing.MD, 0, Spacing.MD, Spacing.MD)
        else:
            layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(0)

        self.window_frame = QWidget(root)
        self.window_frame.setObjectName("windowFrame")
        frame_layout = QVBoxLayout(self.window_frame)
        if sys.platform == "darwin":
            frame_layout.setContentsMargins(Spacing.SM, 34, Spacing.SM, Spacing.SM)
        else:
            frame_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        frame_layout.setSpacing(Spacing.MD)

        self.left_dock = LeftDock(self.window_frame)
        self.left_panel = LeftPanel(self.window_frame)
        self.review_queue_pane = ReviewQueuePane(self.window_frame)
        self.search_pane = SearchPane(self.window_frame)
        self.export_pane = ExportPane(self.window_frame)
        self.timeline_panel = TimelinePanel(
            self.window_frame,
            playback_controller=getattr(self.app_context, "playback_controller", None),
        )
        self.right_dock = RightDock(self.window_frame)
        self.right_panel = RightPanel(self.window_frame)
        self.inspector_detail_pane = InspectorDetailPane(self.window_frame)
        self.bottom_panel = BottomPanel(self.window_frame)

        self._configure_left_dock()
        self._configure_right_dock()

        self.content_splitter = ModernSplitter(Qt.Orientation.Vertical, self.window_frame)
        self.content_splitter.addWidget(self.timeline_panel)
        self.content_splitter.addWidget(self.bottom_panel)
        self.content_splitter.setStretchFactor(0, 7)
        self.content_splitter.setStretchFactor(1, 3)
        self.content_splitter.setSizes([720, 230])

        self.shell_splitter = ModernSplitter(Qt.Orientation.Horizontal, self.window_frame)
        self.shell_splitter.addWidget(self.left_dock)
        self.shell_splitter.addWidget(self.content_splitter)
        self.shell_splitter.addWidget(self.right_dock)
        self.shell_splitter.setStretchFactor(0, 0)
        self.shell_splitter.setStretchFactor(1, 1)
        self.shell_splitter.setStretchFactor(2, 0)
        self.shell_splitter.setSizes([314, 926, 360])
        self.shell_splitter.splitterMoved.connect(self._remember_shell_dock_widths)

        frame_layout.addWidget(self.shell_splitter, 1)
        layout.addWidget(self.window_frame, 1)

        self._apply_left_pane_state(self._active_left_pane_id)
        self._apply_right_pane_state(self._active_right_pane_id)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if sys.platform == "darwin" and not self._macos_chrome_applied:
            apply_integrated_macos_chrome(self)
            self._macos_chrome_applied = True

    def _configure_left_dock(self) -> None:
        style = self.style()
        pane_specs = (
            LeftPaneSpec("corpus", "Project", style.standardIcon(QStyle.StandardPixmap.SP_DirIcon), self.left_panel),
            LeftPaneSpec("review", "Review Queue", style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning), self.review_queue_pane),
            LeftPaneSpec("search", "Search", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), self.search_pane),
            LeftPaneSpec("exports", "Exports", style.standardIcon(QStyle.StandardPixmap.SP_DriveFDIcon), self.export_pane),
        )
        for spec in pane_specs:
            self.left_dock.add_pane(spec)
        self.left_dock.pane_requested.connect(self._toggle_left_pane)

    def _configure_right_dock(self) -> None:
        style = self.style()
        pane_specs = (
            RightPaneSpec("analysis", "Analysis", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), self.right_panel),
            RightPaneSpec("inspector", "Inspector", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), self.inspector_detail_pane),
        )
        for spec in pane_specs:
            self.right_dock.add_pane(spec)
        self.right_dock.pane_requested.connect(self._toggle_right_pane)

    def _toggle_left_pane(self, pane_id: str) -> None:
        next_pane_id = None if self._active_left_pane_id == pane_id else pane_id
        self._apply_left_pane_state(next_pane_id)

    def _apply_left_pane_state(self, pane_id: str | None) -> None:
        self._active_left_pane_id = pane_id
        self.left_dock.set_active_pane(pane_id)
        self._update_shell_sizes()

    def _toggle_right_pane(self, pane_id: str) -> None:
        next_pane_id = None if self._active_right_pane_id == pane_id else pane_id
        self._apply_right_pane_state(next_pane_id)

    def _apply_right_pane_state(self, pane_id: str | None) -> None:
        self._active_right_pane_id = pane_id
        self.right_dock.set_active_pane(pane_id)
        self._update_shell_sizes()

    def _update_shell_sizes(self) -> None:
        total_width = max(self.shell_splitter.width(), 1_500)
        if self._active_left_pane_id is None:
            left_width = self.left_dock.tool_bar.width()
        else:
            left_width = self.left_dock.tool_bar.width() + self.left_dock.pane_container.expanded_width
        if self._active_right_pane_id is None:
            right_width = self.right_dock.tool_bar.width()
        else:
            right_width = self.right_dock.tool_bar.width() + self.right_dock.pane_container.expanded_width
        content_width = max(760, total_width - left_width - right_width)
        self.shell_splitter.setSizes([left_width, content_width, right_width])

    def _remember_shell_dock_widths(self, pos: int, index: int) -> None:
        _ = pos
        sizes = self.shell_splitter.sizes()
        if self._active_left_pane_id is not None:
            visible_left_width = sizes[0] - self.left_dock.tool_bar.width()
            if visible_left_width > 180:
                self.left_dock.pane_container.set_expanded_width(visible_left_width)
        if self._active_right_pane_id is not None:
            visible_right_width = sizes[2] - self.right_dock.tool_bar.width()
            if visible_right_width > 220:
                self.right_dock.pane_container.set_expanded_width(visible_right_width)
