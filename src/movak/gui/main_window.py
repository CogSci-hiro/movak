from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence, QShowEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QStyle, QVBoxLayout, QWidget

from ..app.session_manager import SessionManager
from ..audio.playback import AudioPlaybackService
from ..audio.waveform_cache import WaveformCache
from .app_context import AppContext
from .controllers.analysis_inspector_controller import AnalysisInspectorController
from .controllers.navigation_controller import NavigationController
from .controllers.playback_controller import PlaybackController
from .components.left_dock import LeftDock, LeftPaneSpec
from .components.macos_window import apply_integrated_macos_chrome
from .components.modern_splitter import ModernSplitter
from .components.right_dock import RightDock, RightPaneSpec
from .components.settings_dialog import SettingsDialog
from .panels.bottom_panel import BottomPanel
from .panels.left_panel import ExportPane, LeftPanel, ReviewQueuePane, SearchPane
from .panels.right_panel import InspectorDetailPane, RightPanel
from .panels.timeline_panel import TimelinePanel
from .style.spacing import Spacing
from .style.theme import apply_theme


class MainWindow(QMainWindow):
    """Main IDE-like window composed from thin GUI placeholders."""

    session_state_changed = pyqtSignal()
    DEFAULT_BOTTOM_TOOL_ID = "review_panel"

    def __init__(
        self,
        app_context: AppContext | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        super().__init__()
        self.app_context = app_context or AppContext()
        self.session_manager = session_manager or SessionManager(parent=self)
        self._active_left_pane_id: str | None = "corpus"
        self._active_right_pane_id: str | None = "analysis"
        self._active_bottom_tool_id: str | None = self.DEFAULT_BOTTOM_TOOL_ID
        self._is_bottom_panel_visible = True
        self._macos_chrome_applied = False

        app = QApplication.instance()
        if app is not None:
            apply_theme(app)

        self.playback_service = AudioPlaybackService(self)
        self.waveform_cache = WaveformCache()
        self.playback_controller: PlaybackController | None = None
        self.navigation_controller: NavigationController | None = None
        self.analysis_inspector_controller: AnalysisInspectorController | None = None

        self.setWindowTitle("Movak")
        self.setMinimumSize(960, 640)
        self.resize(1600, 980)
        self._configure_native_chrome()
        self._build_ui()
        self._configure_playback()
        self._configure_navigation()
        self._configure_analysis_inspector()
        self._configure_menu_bar()
        self.statusBar().showMessage("Ready", 2_000)
        self.session_manager.attach(self)
        self.session_manager.restore(self)

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

        self.apply_left_panel_state(self._active_left_pane_id)
        self.apply_right_panel_state(self._active_right_pane_id)

    def _configure_playback(self) -> None:
        self.playback_controller = PlaybackController(
            self.playback_service,
            self.timeline_panel.transport_bar,
            self.waveform_cache,
            self.timeline_panel.waveform_track,
            self.timeline_panel.spectrogram_track,
            self.timeline_panel.viewport,
            dialog_parent=self,
            status_message_sink=self.statusBar().showMessage,
        )
        self.app_context.controllers["playback"] = self.playback_controller
        self.app_context.playback_controller = self.playback_controller

    def _configure_navigation(self) -> None:
        self.navigation_controller = NavigationController(self.timeline_panel.viewport, self.playback_service)
        self.timeline_panel.transport_bar.fit_requested.connect(self.navigation_controller.fit_to_audio)
        self.timeline_panel.transport_bar.center_on_playhead_requested.connect(self.navigation_controller.center_on_playhead)
        self.app_context.controllers["navigation"] = self.navigation_controller
        self.app_context.navigation_controller = self.navigation_controller

    def _configure_analysis_inspector(self) -> None:
        self.analysis_inspector_controller = AnalysisInspectorController(
            self.waveform_cache,
            self.timeline_panel.viewport,
            self.timeline_panel.transport_bar,
            self.right_panel,
        )
        if self.playback_controller is not None:
            self.playback_controller.audio_file_loaded.connect(
                lambda _path: self.analysis_inspector_controller.refresh(self.timeline_panel.viewport.cursor_time)
            )

    def _configure_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        open_audio_action = QAction("Open audio...", self)
        open_audio_action.setShortcut("Ctrl+O")
        open_audio_action.triggered.connect(self._open_audio_file)
        file_menu.addAction(open_audio_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.settings_action = QAction("Settings...", self)
        self.settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        self.settings_action.triggered.connect(self._open_settings_dialog)
        edit_menu.addAction(self.settings_action)

        view_menu = self.menuBar().addMenu("&View")
        fit_action = QAction("Fit to File", self)
        fit_action.setShortcut("F")
        fit_action.triggered.connect(self._fit_to_file)
        view_menu.addAction(fit_action)

        center_action = QAction("Center on Playhead", self)
        center_action.setShortcut("C")
        center_action.triggered.connect(self._center_on_playhead)
        view_menu.addAction(center_action)

        self.toggle_bottom_panel_action = QAction("Show Review Panel", self)
        self.toggle_bottom_panel_action.setCheckable(True)
        self.toggle_bottom_panel_action.setChecked(True)
        self.toggle_bottom_panel_action.toggled.connect(self.set_bottom_panel_visible)
        view_menu.addAction(self.toggle_bottom_panel_action)

    def _open_audio_file(self) -> None:
        if self.playback_controller is None:
            return
        self.playback_controller.open_audio_file()

    def _fit_to_file(self) -> None:
        if self.navigation_controller is None:
            return
        self.navigation_controller.fit_to_audio()

    def _center_on_playhead(self) -> None:
        if self.navigation_controller is None:
            return
        self.navigation_controller.center_on_playhead()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(
            reopen_last_audio_on_launch=self.session_manager.reopen_last_audio_on_launch(),
            parent=self,
        )
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            return
        self.session_manager.set_reopen_last_audio_on_launch(dialog.reopen_last_audio_on_launch())

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if sys.platform == "darwin" and not self._macos_chrome_applied:
            apply_integrated_macos_chrome(self)
            self._macos_chrome_applied = True

    def closeEvent(self, event: QCloseEvent) -> None:
        self.session_manager.save(self)
        super().closeEvent(event)

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
        self.left_dock.add_bottom_tool(
            self.DEFAULT_BOTTOM_TOOL_ID,
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView),
            "Review",
        )
        self.left_dock.pane_requested.connect(self._toggle_left_pane)
        self.left_dock.bottom_tool_requested.connect(self._toggle_bottom_tool)

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
        self.apply_left_panel_state(next_pane_id)

    @property
    def active_left_pane_id(self) -> str | None:
        """Return the currently expanded left pane identifier."""

        return self._active_left_pane_id

    @property
    def active_right_pane_id(self) -> str | None:
        """Return the currently expanded right pane identifier."""

        return self._active_right_pane_id

    def apply_left_panel_state(self, pane_id: str | None) -> None:
        """Apply the requested left pane state and notify persistence."""

        self._active_left_pane_id = pane_id
        self.left_dock.set_active_pane(pane_id)
        self._update_shell_sizes()
        self.session_state_changed.emit()

    def _toggle_right_pane(self, pane_id: str) -> None:
        next_pane_id = None if self._active_right_pane_id == pane_id else pane_id
        self.apply_right_panel_state(next_pane_id)

    def apply_right_panel_state(self, pane_id: str | None) -> None:
        """Apply the requested right pane state and notify persistence."""

        self._active_right_pane_id = pane_id
        self.right_dock.set_active_pane(pane_id)
        self._update_shell_sizes()
        self.session_state_changed.emit()

    def _toggle_bottom_tool(self, tool_id: str) -> None:
        next_tool_id = None if self._is_bottom_panel_visible and self._active_bottom_tool_id == tool_id else tool_id
        self.apply_bottom_tool_state(next_tool_id)

    def apply_bottom_tool_state(self, tool_id: str | None) -> None:
        """Apply the requested bottom tool state while preserving splitter behavior."""

        self._active_bottom_tool_id = tool_id
        self.left_dock.set_active_bottom_tool(tool_id if tool_id is not None and self._is_bottom_panel_visible else None)
        self.set_bottom_panel_visible(tool_id is not None)

    def set_bottom_panel_visible(self, visible: bool) -> None:
        """Show or hide the bottom review panel.

        Notes
        -----
        The session manager restores this before splitter sizes so the splitter
        snapshot can safely reapply the correct visible or collapsed heights.
        """

        if visible and self._active_bottom_tool_id is None:
            self._active_bottom_tool_id = self.DEFAULT_BOTTOM_TOOL_ID

        self._is_bottom_panel_visible = visible
        self.bottom_panel.setVisible(visible)
        self.left_dock.set_active_bottom_tool(self._active_bottom_tool_id if visible else None)
        self.toggle_bottom_panel_action.blockSignals(True)
        self.toggle_bottom_panel_action.setChecked(visible)
        self.toggle_bottom_panel_action.blockSignals(False)

        if visible:
            current_sizes = self.content_splitter.sizes()
            restored_top_size = current_sizes[0] if len(current_sizes) > 1 and current_sizes[0] > 0 else 720
            restored_bottom_size = current_sizes[1] if len(current_sizes) > 1 and current_sizes[1] > 0 else 230
            self.content_splitter.setSizes([restored_top_size, restored_bottom_size])
        else:
            self.content_splitter.setSizes([max(self.content_splitter.height(), 1), 0])
        self.session_state_changed.emit()

    def is_bottom_panel_visible(self) -> bool:
        """Return whether the bottom review panel is visible."""

        return self._is_bottom_panel_visible

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
