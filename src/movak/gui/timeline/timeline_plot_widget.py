from __future__ import annotations

import math

import pyqtgraph as pg
from PyQt6.QtCore import QEvent, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QNativeGestureEvent

from .navigation_viewbox import TimelineViewBox

MIN_GESTURE_SCALE = 0.25
MAX_GESTURE_SCALE = 4.0


class TimelinePlotWidget(pg.PlotWidget):
    """Plot widget that surfaces macOS native pinch gestures for timeline zoom."""

    native_zoom_requested = pyqtSignal(float, float)

    def __init__(self, view_box: TimelineViewBox, parent=None) -> None:
        super().__init__(parent=parent, viewBox=view_box)

    def event(self, event) -> bool:
        """Handle native trackpad zoom gestures on macOS."""
        if event.type() == QEvent.Type.NativeGesture:
            native_event = event
            if self._handle_native_gesture(native_event):
                return True
        return super().event(event)

    def _handle_native_gesture(self, event: QNativeGestureEvent) -> bool:
        gesture_type = event.gestureType()
        if gesture_type != Qt.NativeGestureType.ZoomNativeGesture:
            return False

        scale_factor = _native_zoom_value_to_scale(event.value())
        widget_position = event.position().toPoint() if hasattr(event.position(), "toPoint") else QPoint()
        scene_position = self.mapToScene(widget_position)
        anchor_point = self.getViewBox().mapSceneToView(scene_position)
        self.native_zoom_requested.emit(anchor_point.x(), scale_factor)
        event.accept()
        return True


def _native_zoom_value_to_scale(gesture_value: float) -> float:
    """Convert a native magnification delta into a timeline width scale factor."""
    scale_factor = math.pow(2.0, -gesture_value)
    return min(max(scale_factor, MIN_GESTURE_SCALE), MAX_GESTURE_SCALE)
