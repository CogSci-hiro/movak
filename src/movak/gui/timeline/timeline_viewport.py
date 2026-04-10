from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QScrollArea, QScrollBar, QVBoxLayout, QWidget

from ..style.spacing import Spacing
from .scrollbar_sync import scrollbar_value_to_time_range, visible_range_to_scrollbar_state
from .time_axis import TimeAxis
from .timeline_track import TimelineTrack

DEFAULT_VISIBLE_START_TIME = 0.0
DEFAULT_VISIBLE_DURATION = 6.0
MIN_VISIBLE_DURATION = 0.05
MAX_VISIBLE_DURATION = 300.0
RANGE_TOLERANCE_SECONDS = 1e-6
SCROLLBAR_HEIGHT = 18


class TimelineViewport(QWidget):
    """Shared timeline viewport that coordinates time axis, tracks, and scrollbar."""

    time_selected = pyqtSignal(float)

    def __init__(self, total_duration: float = 30.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.total_duration = max(total_duration, DEFAULT_VISIBLE_DURATION)
        self.visible_start_time = DEFAULT_VISIBLE_START_TIME
        self.visible_end_time = min(DEFAULT_VISIBLE_DURATION, self.total_duration)
        self.cursor_time = self.visible_start_time
        self.tracks: list[TimelineTrack] = []
        self._synchronizing_range = False

        self.time_axis = TimeAxis(self)
        self.time_axis.set_time_bounds(self.total_duration)
        self.time_axis.set_time_range(self.visible_start_time, self.visible_end_time)
        self.time_axis.plot_widget.getViewBox().sigXRangeChanged.connect(self._handle_view_range_changed)
        self.time_axis.plot_widget.native_zoom_requested.connect(self.zoom_x_around_time)

        self._track_container = QWidget(self)
        self._track_layout = QVBoxLayout()
        self._track_layout.setContentsMargins(0, 0, 0, 0)
        self._track_layout.setSpacing(Spacing.SM)
        self._track_container.setLayout(self._track_layout)

        self._track_scroll_area = QScrollArea(self)
        self._track_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._track_scroll_area.setWidgetResizable(True)
        self._track_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._track_scroll_area.setWidget(self._track_container)

        self.horizontal_scrollbar = QScrollBar(self)
        self.horizontal_scrollbar.setOrientation(Qt.Orientation.Horizontal)
        self.horizontal_scrollbar.setFixedHeight(SCROLLBAR_HEIGHT)
        self.horizontal_scrollbar.setObjectName("timelineHorizontalScrollbar")
        self.horizontal_scrollbar.valueChanged.connect(self._handle_scrollbar_value_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        layout.addWidget(self.time_axis)
        layout.addWidget(self._track_scroll_area, 1)
        layout.addWidget(self.horizontal_scrollbar)

        self._update_scrollbar()

    def add_track(self, track: TimelineTrack) -> None:
        """Add a track to the shared timeline stack."""
        track.attach_viewport(self)
        track.set_time_bounds(self.total_duration)
        track.set_cursor_time(self.cursor_time)
        track.plot_widget.getViewBox().sigXRangeChanged.connect(self._handle_view_range_changed)
        track.plot_widget.native_zoom_requested.connect(self.zoom_x_around_time)
        track.time_clicked.connect(self._handle_time_clicked)
        self.tracks.append(track)
        self._track_layout.addWidget(track)
        track.set_time_range(self.visible_start_time, self.visible_end_time)

    def add_tracks(self, tracks: Iterable[TimelineTrack]) -> None:
        """Add multiple tracks in order."""
        for track in tracks:
            self.add_track(track)

    def set_total_duration(self, total_duration: float) -> None:
        """Update the total timeline duration and reset the visible window."""
        self.total_duration = max(total_duration, MIN_VISIBLE_DURATION)
        self.time_axis.set_time_bounds(self.total_duration)
        for track in self.tracks:
            track.set_time_bounds(self.total_duration)
        self.fit_to_audio()
        self.set_cursor_time(min(self.cursor_time, self.total_duration))

    def fit_to_audio(self) -> None:
        """Reset the visible range to the full loaded audio."""
        self.set_visible_time_range(0.0, self.total_duration)

    def center_on_time(self, time_s: float) -> None:
        """Center the current visible window around a playback time."""
        visible_duration = self.visible_end_time - self.visible_start_time
        half_duration = visible_duration / 2.0
        self.set_visible_time_range(time_s - half_duration, time_s + half_duration)

    def zoom_x_around_time(self, center_time_s: float, scale_factor: float) -> None:
        """Zoom the visible x-range around a time anchor."""
        current_duration = self.visible_end_time - self.visible_start_time
        new_duration = min(
            max(current_duration * scale_factor, MIN_VISIBLE_DURATION),
            min(MAX_VISIBLE_DURATION, self.total_duration),
        )
        if current_duration <= 0.0:
            anchor_ratio = 0.5
        else:
            anchor_ratio = (center_time_s - self.visible_start_time) / current_duration
        anchor_ratio = min(max(anchor_ratio, 0.0), 1.0)
        new_start = center_time_s - (new_duration * anchor_ratio)
        self.set_visible_time_range(new_start, new_start + new_duration)

    def set_visible_time_range(self, start_time: float, end_time: float) -> None:
        """Update the visible time window for all tracks."""
        clamped_start, clamped_end = self.clamp_visible_range(start_time, end_time)

        if (
            abs(clamped_start - self.visible_start_time) <= RANGE_TOLERANCE_SECONDS
            and abs(clamped_end - self.visible_end_time) <= RANGE_TOLERANCE_SECONDS
        ):
            self._update_scrollbar()
            return

        self.visible_start_time = clamped_start
        self.visible_end_time = clamped_end

        self._synchronizing_range = True
        try:
            self.time_axis.set_time_range(clamped_start, clamped_end)
            for track in self.tracks:
                track.set_time_range(clamped_start, clamped_end)
        finally:
            self._synchronizing_range = False
        self._update_scrollbar()

    def set_visible_range(self, start_time: float, end_time: float) -> None:
        """Backward-compatible alias for setting the time range."""
        self.set_visible_time_range(start_time, end_time)

    def clamp_visible_range(self, start_time: float, end_time: float) -> tuple[float, float]:
        """Clamp a requested range into the valid audio duration."""
        duration = max(end_time - start_time, MIN_VISIBLE_DURATION)
        duration = min(duration, MAX_VISIBLE_DURATION, self.total_duration)
        max_start_time = max(0.0, self.total_duration - duration)
        clamped_start = min(max(0.0, start_time), max_start_time)
        clamped_end = min(self.total_duration, clamped_start + duration)
        return clamped_start, max(clamped_start + MIN_VISIBLE_DURATION, clamped_end)

    def set_cursor_time(self, cursor_time: float) -> None:
        """Move the vertical playback cursor across all tracks."""
        self.cursor_time = min(max(cursor_time, 0.0), self.total_duration)
        for track in self.tracks:
            track.set_cursor_time(self.cursor_time)

    def _handle_time_clicked(self, time_s: float) -> None:
        clamped_time = min(max(time_s, 0.0), self.total_duration)
        self.set_cursor_time(clamped_time)
        self.time_selected.emit(clamped_time)

    def _handle_view_range_changed(self, _view_box, view_range) -> None:
        if self._synchronizing_range:
            return
        start_time, end_time = view_range
        self.set_visible_time_range(start_time, end_time)

    def _handle_scrollbar_value_changed(self, value: int) -> None:
        visible_duration = self.visible_end_time - self.visible_start_time
        start_time_s, end_time_s = scrollbar_value_to_time_range(
            total_duration_s=self.total_duration,
            visible_duration_s=visible_duration,
            start_value=value,
        )
        self.set_visible_time_range(start_time_s, end_time_s)

    def _update_scrollbar(self) -> None:
        scrollbar_state = visible_range_to_scrollbar_state(
            total_duration_s=self.total_duration,
            visible_start_s=self.visible_start_time,
            visible_end_s=self.visible_end_time,
        )
        blocker = QSignalBlocker(self.horizontal_scrollbar)
        self.horizontal_scrollbar.setMinimum(scrollbar_state.minimum)
        self.horizontal_scrollbar.setMaximum(scrollbar_state.maximum)
        self.horizontal_scrollbar.setPageStep(scrollbar_state.page_step)
        self.horizontal_scrollbar.setSingleStep(scrollbar_state.single_step)
        self.horizontal_scrollbar.setValue(scrollbar_state.value)
        self.horizontal_scrollbar.setEnabled(scrollbar_state.enabled)
        # Keep the timeline scrollbar visible at all times so users can
        # immediately see where horizontal panning lives after zooming.
        self.horizontal_scrollbar.setVisible(True)
        del blocker
