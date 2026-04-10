"""Centralized session persistence for the Movak GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, QTimer

from .state import AppState, deserialize_app_state, serialize_app_state

SAVE_DEBOUNCE_MS = 150
SETTINGS_ORGANIZATION = "Movak"
SETTINGS_APPLICATION = "Movak"


class SessionManager(QObject):
    """Capture, restore, and persist application UI/session state.

    Notes
    -----
    This manager keeps all ``QSettings`` access in one place so widgets do not
    need to know about persistence details.
    """

    def __init__(self, settings: QSettings | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings or QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        self._is_restoring_state = False
        self._pending_file_view_state: AppState | None = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._main_window = None

    @property
    def is_restoring_state(self) -> bool:
        """Return whether a restore operation is in progress."""

        return self._is_restoring_state

    def attach(self, main_window) -> None:
        """Connect the manager to a fully built main window.

        Parameters
        ----------
        main_window:
            Main window instance to observe and persist.
        """

        self._main_window = main_window
        self._save_timer.timeout.connect(lambda: self.save(main_window))
        main_window.session_state_changed.connect(self.schedule_save)
        main_window.content_splitter.splitterMoved.connect(self.schedule_save)
        main_window.shell_splitter.splitterMoved.connect(self.schedule_save)
        main_window.timeline_panel.transport_bar.loop_button.toggled.connect(self.schedule_save)
        main_window.timeline_panel.transport_bar.waveform_mode_combo.currentIndexChanged.connect(self.schedule_save)
        main_window.playback_controller.audio_file_loaded.connect(self._handle_audio_file_loaded)

    def restore(self, main_window) -> AppState:
        """Restore persisted UI state and reopen the last file when possible.

        Parameters
        ----------
        main_window:
            Main window instance to restore.

        Returns
        -------
        AppState
            The state loaded from settings.
        """

        state = self._read_state()
        self._pending_file_view_state = state
        self._is_restoring_state = True
        try:
            # Suppress save-side effects while replaying persisted state.
            self._restore_main_window_state(main_window, state)
            self._restore_global_ui_preferences(main_window, state)

            if state.last_opened_file and Path(state.last_opened_file).exists():
                if not main_window.playback_controller.open_audio_path(state.last_opened_file):
                    self._pending_file_view_state = None
            else:
                self._pending_file_view_state = None
        finally:
            self._is_restoring_state = False
        return state

    def capture(self, main_window) -> AppState:
        """Capture the current app state from the main window.

        Parameters
        ----------
        main_window:
            Main window to read from.

        Returns
        -------
        AppState
            Snapshot of the current persisted state.
        """

        transport_bar = main_window.timeline_panel.transport_bar
        shell_sizes = tuple(main_window.shell_splitter.sizes())
        content_sizes = tuple(main_window.content_splitter.sizes())
        return AppState(
            last_opened_file=main_window.playback_service.current_path or None,
            left_panel_visible=main_window.active_left_pane_id is not None,
            right_panel_visible=main_window.active_right_pane_id is not None,
            bottom_panel_visible=main_window.is_bottom_panel_visible(),
            active_left_pane_id=main_window.active_left_pane_id,
            active_right_pane_id=main_window.active_right_pane_id,
            loop_enabled=transport_bar.loop_button.isChecked(),
            waveform_display_mode=transport_bar.current_waveform_display_mode(),
            shell_splitter_sizes=self._normalize_shell_sizes(shell_sizes),
            content_splitter_sizes=self._normalize_content_sizes(content_sizes, main_window.is_bottom_panel_visible()),
            left_panel_width=main_window.left_dock.pane_container.expanded_width,
            right_panel_width=main_window.right_dock.pane_container.expanded_width,
            main_window_geometry=main_window.saveGeometry(),
            main_window_state=main_window.saveState(),
        )

    def save(self, main_window=None) -> None:
        """Persist the current state immediately."""

        if self._is_restoring_state:
            return
        window = main_window or self._main_window
        if window is None:
            return
        state = self.capture(window)
        self._write_global_ui_preferences(state)
        self._write_session_state(state)
        self.settings.sync()

    def schedule_save(self) -> None:
        """Persist state soon, while coalescing noisy repeated updates."""

        if self._is_restoring_state or self._main_window is None:
            return
        self._save_timer.start()

    def _read_state(self) -> AppState:
        """Load the complete persisted state from settings."""

        raw_values: dict[str, object] = {}
        for key in serialize_app_state(AppState()):
            raw_values[key] = self.settings.value(key)
        return deserialize_app_state(raw_values)

    def _write_global_ui_preferences(self, state: AppState) -> None:
        """Persist window and view preferences."""

        values = serialize_app_state(state)
        for key in (
            "main_window/geometry",
            "main_window/window_state",
            "view/loop_enabled",
            "view/waveform_display_mode",
            "splitters/main",
            "splitters/center",
        ):
            self.settings.setValue(key, values[key])

    def _write_session_state(self, state: AppState) -> None:
        """Persist session-specific state such as the last opened file."""

        values = serialize_app_state(state)
        for key in (
            "session/last_opened_file",
            "session/left_panel_visible",
            "session/right_panel_visible",
            "session/bottom_panel_visible",
            "session/active_left_pane",
            "session/active_right_pane",
            "session/left_panel_width",
            "session/right_panel_width",
        ):
            self.settings.setValue(key, values[key])

    def _restore_main_window_state(self, main_window, state: AppState) -> None:
        """Restore Qt-managed geometry before widget-level state."""

        if state.main_window_geometry is not None:
            main_window.restoreGeometry(state.main_window_geometry)
        if state.main_window_state is not None:
            main_window.restoreState(state.main_window_state)

    def _restore_global_ui_preferences(self, main_window, state: AppState) -> None:
        """Restore UI preferences after the window is fully constructed."""

        if state.left_panel_width is not None:
            main_window.left_dock.pane_container.set_expanded_width(state.left_panel_width)
        if state.right_panel_width is not None:
            main_window.right_dock.pane_container.set_expanded_width(state.right_panel_width)

        main_window.set_bottom_panel_visible(state.bottom_panel_visible)
        main_window.apply_left_panel_state(
            state.active_left_pane_id if state.left_panel_visible else None,
        )
        main_window.apply_right_panel_state(
            state.active_right_pane_id if state.right_panel_visible else None,
        )
        main_window.timeline_panel.transport_bar.loop_button.setChecked(state.loop_enabled)
        main_window.content_splitter.setSizes(list(state.content_splitter_sizes))
        main_window.shell_splitter.setSizes(list(state.shell_splitter_sizes))

    def _restore_file_dependent_state(self, main_window, state: AppState) -> None:
        """Restore view state that requires an open file first.

        Notes
        -----
        Waveform mode restore is deferred until after file load so stereo-only
        controls have already been populated.
        """

        main_window.timeline_panel.transport_bar.set_waveform_display_mode(state.waveform_display_mode)

    def _handle_audio_file_loaded(self, _path: str) -> None:
        """Restore deferred file-dependent state and optionally save."""

        if self._main_window is None:
            return
        if self._pending_file_view_state is not None:
            self._restore_file_dependent_state(self._main_window, self._pending_file_view_state)
            self._pending_file_view_state = None
        if not self._is_restoring_state:
            self.schedule_save()

    def _normalize_shell_sizes(self, sizes: tuple[int, ...]) -> tuple[int, int, int]:
        """Ensure shell splitter sizes have the expected shape."""

        if len(sizes) == 3 and all(size >= 0 for size in sizes):
            return int(sizes[0]), int(sizes[1]), int(sizes[2])
        return AppState().shell_splitter_sizes

    def _normalize_content_sizes(self, sizes: tuple[int, ...], bottom_panel_visible: bool) -> tuple[int, int]:
        """Normalize content splitter sizes while preserving hidden state."""

        if len(sizes) != 2:
            return AppState().content_splitter_sizes
        top_size = max(int(sizes[0]), 0)
        bottom_size = max(int(sizes[1]), 0)
        if not bottom_panel_visible:
            return top_size, 0
        return top_size, bottom_size
