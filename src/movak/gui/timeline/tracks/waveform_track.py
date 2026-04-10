from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtCore import QTimer

from ....audio.waveform_cache import POINTS_PER_PIXEL, WaveformData, empty_waveform_data, get_visible_waveform
from ...style.palette import Palette
from ..timeline_track import TimelineTrack

WAVEFORM_DEFAULT_HEIGHT = 120
WAVEFORM_LINE_WIDTH = 1
MIN_VIEWPORT_PIXEL_WIDTH = 64
DEFAULT_EMPTY_RANGE_SECONDS = 1.0
DISPLAY_MODE_MONO = "mono"
DISPLAY_MODE_STEREO = "stereo"
STEREO_CHANNEL_GAIN = 0.45
STEREO_TOP_OFFSET = 0.55
STEREO_BOTTOM_OFFSET = -0.55


class WaveformTrack(TimelineTrack):
    """Waveform row rendered against the shared timeline axis."""

    def __init__(self, parent=None) -> None:
        super().__init__("waveform", parent)
        self.waveform_data = empty_waveform_data()
        self.display_mode = DISPLAY_MODE_MONO
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_visible_waveform)

        self.plot_widget.setYRange(-1.05, 1.05, padding=0.0)
        self.plot_widget.setLimits(yMin=-1.1, yMax=1.1)
        self.plot_widget.getPlotItem().setLabel("bottom", text="Time (s)")
        self.plot_widget.hideAxis("bottom")

        waveform_pen = pg.mkPen(Palette.WAVEFORM, width=WAVEFORM_LINE_WIDTH)
        self.waveform_item = self.plot_widget.plot(
            pen=waveform_pen,
            antialias=False,
        )
        self.waveform_item.setClipToView(True)
        self.waveform_item.setDownsampling(auto=True, method="peak")

        left_channel_pen = pg.mkPen(Palette.WAVEFORM, width=WAVEFORM_LINE_WIDTH)
        right_channel_pen = pg.mkPen(Palette.ACCENT_VIOLET, width=WAVEFORM_LINE_WIDTH)
        self.left_channel_item = self.plot_widget.plot(pen=left_channel_pen, antialias=False)
        self.left_channel_item.setClipToView(True)
        self.left_channel_item.setDownsampling(auto=True, method="peak")
        self.right_channel_item = self.plot_widget.plot(pen=right_channel_pen, antialias=False)
        self.right_channel_item.setClipToView(True)
        self.right_channel_item.setDownsampling(auto=True, method="peak")
        self.left_channel_item.setVisible(False)
        self.right_channel_item.setVisible(False)

        self.setMinimumHeight(WAVEFORM_DEFAULT_HEIGHT)

        self.plot_widget.getViewBox().sigXRangeChanged.connect(self._schedule_refresh)
        self.clear_waveform()

    def set_waveform_data(self, waveform_data: WaveformData) -> None:
        """Set waveform data and redraw the track."""
        self.waveform_data = waveform_data
        self.render(self.visible_start_time, self.visible_end_time)

    def clear_waveform(self) -> None:
        """Reset the track to an empty waveform state."""
        self.waveform_data = empty_waveform_data()
        self.waveform_item.setData([], [])
        self.left_channel_item.setData([], [])
        self.right_channel_item.setData([], [])
        self.render(self.visible_start_time, self.visible_end_time)

    def set_display_mode(self, mode: str) -> None:
        """Set waveform display mode to ``mono`` or ``stereo``."""
        normalized_mode = DISPLAY_MODE_STEREO if mode == DISPLAY_MODE_STEREO else DISPLAY_MODE_MONO
        if normalized_mode == self.display_mode:
            return
        self.display_mode = normalized_mode
        self._schedule_refresh()

    def render(self, start_time: float, end_time: float) -> None:
        """Keep the waveform track aligned to the current time range."""
        if self.waveform_data.duration_seconds <= 0.0:
            self.plot_widget.setXRange(0.0, max(end_time, DEFAULT_EMPTY_RANGE_SECONDS), padding=0.0)
            self.waveform_item.setData([], [])
            self.left_channel_item.setData([], [])
            self.right_channel_item.setData([], [])
            return

        clamped_start_time = max(0.0, start_time)
        clamped_end_time = max(clamped_start_time, min(end_time, self.waveform_data.duration_seconds))
        self.plot_widget.setXRange(clamped_start_time, clamped_end_time, padding=0.0)
        self._schedule_refresh()

    def resizeEvent(self, event) -> None:
        """Refresh the visible waveform when viewport width changes."""
        super().resizeEvent(event)
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        self._refresh_timer.start(0)

    def _refresh_visible_waveform(self) -> None:
        if self.waveform_data.duration_seconds <= 0.0:
            return

        visible_range, _y_range = self.plot_widget.getViewBox().viewRange()
        start_time, end_time = visible_range
        target_num_points = max(MIN_VIEWPORT_PIXEL_WIDTH, self.plot_widget.viewport().width() * POINTS_PER_PIXEL)
        if self.display_mode == DISPLAY_MODE_STEREO and self.waveform_data.has_stereo:
            channel_samples = self.waveform_data.channel_samples
            if channel_samples is None or channel_samples.shape[1] < 2:
                self._set_mono_visible_waveform(start_time, end_time, target_num_points)
                return

            left_waveform = get_visible_waveform(
                channel_samples[:, 0],
                self.waveform_data.sample_rate,
                start_time,
                end_time,
                target_num_points,
            )
            right_waveform = get_visible_waveform(
                channel_samples[:, 1],
                self.waveform_data.sample_rate,
                start_time,
                end_time,
                target_num_points,
            )
            self.waveform_item.setVisible(False)
            self.left_channel_item.setVisible(True)
            self.right_channel_item.setVisible(True)
            self.left_channel_item.setData(
                left_waveform.x_values,
                (left_waveform.y_values * STEREO_CHANNEL_GAIN) + STEREO_TOP_OFFSET,
            )
            self.right_channel_item.setData(
                right_waveform.x_values,
                (right_waveform.y_values * STEREO_CHANNEL_GAIN) + STEREO_BOTTOM_OFFSET,
            )
            return

        self._set_mono_visible_waveform(start_time, end_time, target_num_points)

    def _set_mono_visible_waveform(self, start_time: float, end_time: float, target_num_points: int) -> None:
        """Render a single mixed waveform trace."""
        visible_waveform = get_visible_waveform(
            self.waveform_data.samples,
            self.waveform_data.sample_rate,
            start_time,
            end_time,
            target_num_points,
        )
        self.left_channel_item.setVisible(False)
        self.right_channel_item.setVisible(False)
        self.waveform_item.setVisible(True)
        self.waveform_item.setData(visible_waveform.x_values, visible_waveform.y_values)
