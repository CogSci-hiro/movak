from __future__ import annotations

import math

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..style.palette import Palette
from .navigation_viewbox import TimelineViewBox
from .timeline_plot_widget import TimelinePlotWidget
from .timeline_track import TRACK_LEFT_AXIS_WIDTH

TIME_AXIS_HEIGHT = 34
MAJOR_TICK_TARGET_COUNT = 8
TIME_AXIS_LINE_WIDTH = 1
MIN_TIME_RANGE_SECONDS = 0.05


class TimeAxis(QWidget):
    """Shared time ruler aligned with all timeline tracks.

    Parameters
    ----------
    parent
        Optional parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.visible_start_time = 0.0
        self.visible_end_time = 10.0
        self.view_box = TimelineViewBox()

        self.plot_widget = TimelinePlotWidget(self.view_box, parent=self)
        self.plot_widget.setBackground((0, 0, 0, 0))
        self.plot_widget.hideButtons()
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.showAxis("bottom")
        self.plot_widget.showAxis("left")
        self.plot_widget.getAxis("left").setWidth(TRACK_LEFT_AXIS_WIDTH)
        self.plot_widget.getAxis("left").setStyle(showValues=False, tickLength=0)
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen((0, 0, 0, 0)))
        self.plot_widget.getAxis("left").setTickPen(pg.mkPen((0, 0, 0, 0)))
        self.plot_widget.getAxis("bottom").setPen(pg.mkPen(Palette.TEXT_MUTED, width=TIME_AXIS_LINE_WIDTH))
        self.plot_widget.getAxis("bottom").setTextPen(pg.mkPen(Palette.TEXT_MUTED))
        self.plot_widget.getAxis("bottom").setTickPen(pg.mkPen(Palette.BORDER_STRONG, width=1))
        self.view_box.setBackgroundColor(Palette.PANEL)
        self.plot_widget.setYRange(0.0, 1.0, padding=0.0)
        self.plot_widget.setCursor(Qt.CursorShape.OpenHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

        self.setFixedHeight(TIME_AXIS_HEIGHT)
        self._update_ticks()

    def set_time_range(self, start_time: float, end_time: float) -> None:
        """Update the visible time window shown by the axis.

        Parameters
        ----------
        start_time
            Visible range start in seconds.
        end_time
            Visible range end in seconds.
        """

        self.visible_start_time = start_time
        self.visible_end_time = end_time
        self.plot_widget.setXRange(start_time, end_time, padding=0.0)
        self._update_ticks()

    def set_time_bounds(self, total_duration: float) -> None:
        """Clamp axis navigation to the valid audio duration."""
        maximum_duration = max(total_duration, MIN_TIME_RANGE_SECONDS)
        self.view_box.setLimits(
            xMin=0.0,
            xMax=maximum_duration,
            minXRange=MIN_TIME_RANGE_SECONDS,
            maxXRange=maximum_duration,
        )

    def _update_ticks(self) -> None:
        """Recompute major ticks for the current visible range."""

        axis = self.plot_widget.getAxis("bottom")
        span = max(self.visible_end_time - self.visible_start_time, 1e-6)
        tick_step = _select_tick_step(span / MAJOR_TICK_TARGET_COUNT)
        first_tick = math.floor(self.visible_start_time / tick_step) * tick_step

        major_ticks: list[tuple[float, str]] = []
        tick_time = first_tick
        end_limit = self.visible_end_time + tick_step
        while tick_time <= end_limit:
            if tick_time >= self.visible_start_time - tick_step:
                major_ticks.append((tick_time, _format_time_label(tick_time)))
            tick_time += tick_step

        axis.setTicks([major_ticks])


def _select_tick_step(target_step: float) -> float:
    """Return a readable tick step close to the requested interval."""

    tick_steps = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 60.0]
    for candidate in tick_steps:
        if candidate >= target_step:
            return candidate
    return 120.0


def _format_time_label(time_seconds: float) -> str:
    """Format a user-facing time-axis label."""

    if time_seconds < 60.0:
        return f"{time_seconds:.2f}s" if time_seconds < 10.0 else f"{time_seconds:.0f}s"

    minutes = int(time_seconds // 60.0)
    seconds = time_seconds - (minutes * 60.0)
    return f"{minutes:d}:{seconds:04.1f}"
