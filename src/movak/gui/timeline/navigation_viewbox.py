from __future__ import annotations

import pyqtgraph as pg
ZOOM_IN_FACTOR = 0.9
ZOOM_OUT_FACTOR = 1.0 / ZOOM_IN_FACTOR


class TimelineViewBox(pg.ViewBox):
    """ViewBox tuned for horizontal timeline navigation."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setMouseEnabled(x=True, y=False)
        self.setMouseMode(pg.ViewBox.PanMode)
        self.setDefaultPadding(0.0)

    def wheelEvent(self, event, axis=None) -> None:
        """Zoom the x-axis around the cursor position."""
        delta = _event_delta(event)
        if delta == 0:
            event.ignore()
            return

        left_time, right_time = self.viewRange()[0]
        current_duration = max(right_time - left_time, 1e-9)
        zoom_factor = ZOOM_IN_FACTOR if delta > 0 else ZOOM_OUT_FACTOR
        new_duration = current_duration * zoom_factor

        if hasattr(event, "position"):
            scene_position = self.mapSceneToView(event.position())
        else:
            scene_position = self.mapSceneToView(event.scenePos())
        anchor_time = scene_position.x()
        if not (left_time <= anchor_time <= right_time):
            anchor_time = left_time + (current_duration / 2.0)

        anchor_ratio = (anchor_time - left_time) / current_duration if current_duration > 0.0 else 0.5
        new_left_time = anchor_time - (new_duration * anchor_ratio)
        new_right_time = new_left_time + new_duration

        self.setXRange(new_left_time, new_right_time, padding=0.0)
        event.accept()

def _event_delta(event) -> int:
    """Return a wheel delta from either Qt or pyqtgraph event wrappers."""
    if hasattr(event, "delta"):
        try:
            return int(event.delta())
        except TypeError:
            pass
    if hasattr(event, "angleDelta"):
        return int(event.angleDelta().y())
    return 0
