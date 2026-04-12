from __future__ import annotations

from typing import TYPE_CHECKING

import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..style.palette import Palette
from .navigation_viewbox import TimelineViewBox
from .timeline_plot_widget import TimelinePlotWidget

TRACK_MINIMUM_HEIGHT = 72
CURSOR_WIDTH = 2
MIN_TIME_RANGE_SECONDS = 0.05
TRACK_LEFT_AXIS_WIDTH = 48

if TYPE_CHECKING:
    from .timeline_viewport import TimelineViewport


class TimelineTrack(QWidget):
    """Base class for one horizontal timeline row aligned to shared time.

    Parameters
    ----------
    track_name
        Human-readable track name.
    parent
        Optional parent widget.
    """

    time_clicked = pyqtSignal(float)

    def __init__(self, track_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.track_name = track_name
        self.timeline_viewport: TimelineViewport | None = None
        self.visible_start_time = 0.0
        self.visible_end_time = 10.0
        self.view_box = self._create_view_box()

        self.plot_widget = TimelinePlotWidget(self.view_box, parent=self)
        self.plot_widget.setBackground((0, 0, 0, 0))
        self.plot_widget.hideButtons()
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.showGrid(x=False, y=False, alpha=0.0)
        self.plot_widget.showAxis("left")
        self.plot_widget.getAxis("left").setWidth(TRACK_LEFT_AXIS_WIDTH)
        self.plot_widget.getAxis("left").setStyle(showValues=False, tickLength=0)
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen((0, 0, 0, 0)))
        self.plot_widget.getAxis("left").setTickPen(pg.mkPen((0, 0, 0, 0)))
        self.plot_widget.hideAxis("bottom")
        self.view_box.setBorder(None)
        self.view_box.setBackgroundColor(Palette.PANEL)
        self.plot_widget.setCursor(Qt.CursorShape.OpenHandCursor)
        self.plot_widget.scene().sigMouseClicked.connect(self._handle_scene_click)

        cursor_pen = pg.mkPen(Palette.CURSOR, width=CURSOR_WIDTH)
        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen=cursor_pen)
        self.plot_widget.addItem(self.cursor_line)
        self.cursor_line.setZValue(1000)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

        self.setMinimumHeight(TRACK_MINIMUM_HEIGHT)
        self.setAutoFillBackground(False)

    def _create_view_box(self) -> TimelineViewBox:
        """Create the view box used by this track."""

        return TimelineViewBox()

    def attach_viewport(self, timeline_viewport: "TimelineViewport") -> None:
        """Attach the track to the shared timeline viewport.

        Parameters
        ----------
        timeline_viewport
            Shared viewport coordinating range and cursor state.
        """

        self.timeline_viewport = timeline_viewport

    def set_time_range(self, start_time: float, end_time: float) -> None:
        """Update the visible time range and trigger a re-render.

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
        self.render(start_time, end_time)

    def set_cursor_time(self, cursor_time: float) -> None:
        """Move the playback cursor for this track.

        Parameters
        ----------
        cursor_time
            Cursor time in seconds.
        """

        self.cursor_line.setValue(cursor_time)

    def set_time_bounds(self, total_duration: float) -> None:
        """Clamp navigation to the valid audio duration."""
        maximum_duration = max(total_duration, MIN_TIME_RANGE_SECONDS)
        self.view_box.setLimits(
            xMin=0.0,
            xMax=maximum_duration,
            minXRange=MIN_TIME_RANGE_SECONDS,
            maxXRange=maximum_duration,
        )

    def mousePressEvent(self, event) -> None:
        """Allow focus without owning annotation interaction yet."""

        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.plot_widget.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Restore the navigation cursor after dragging."""
        self.plot_widget.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def render(self, start_time: float, end_time: float) -> None:
        """Render the visible segment for this track.

        Parameters
        ----------
        start_time
            Visible range start in seconds.
        end_time
            Visible range end in seconds.
        """
        raise NotImplementedError("TimelineTrack subclasses must implement render().")

    def _handle_scene_click(self, event) -> None:
        """Emit a clicked time when the plot scene is clicked."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.view_box.sceneBoundingRect().contains(event.scenePos()):
            return
        clicked_point = self.view_box.mapSceneToView(event.scenePos())
        self.time_clicked.emit(clicked_point.x())
