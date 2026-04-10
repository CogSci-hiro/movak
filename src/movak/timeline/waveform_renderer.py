"""Waveform rendering helpers built on top of a waveform pyramid."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from movak.timeline.viewport import TimelineViewport
from movak.timeline.waveform_pyramid import WaveformPyramid, WaveformSegment

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover - optional during headless tests
    pg = None

POLYGON_FILL_ALPHA = 70
POLYGON_LINE_WIDTH = 1


@dataclass(slots=True)
class WaveformRenderResult:
    """Waveform envelope data ready for drawing."""

    x_values: np.ndarray
    y_values: np.ndarray
    segment: WaveformSegment


class WaveformRenderer:
    """Render visible waveform data using a waveform pyramid.

    Parameters
    ----------
    pyramid
        Waveform pyramid backing the renderer.
    plot_item
        Optional pyqtgraph plot item updated during render.
    color
        Optional waveform color.
    """

    def __init__(
        self,
        pyramid: WaveformPyramid,
        plot_item=None,
        *,
        color: str = "#4fc1ff",
    ) -> None:
        self.pyramid = pyramid
        self.plot_item = plot_item
        self.color = color
        self._curve_item = None
        self._fill_item = None
        self._upper_curve = None
        self._lower_curve = None

    def render(self, viewport: TimelineViewport) -> WaveformRenderResult:
        """Render the visible waveform segment for a viewport."""

        segment = self.pyramid.get_segment(
            viewport.visible_start_time,
            viewport.visible_end_time,
            viewport.pixels_per_second,
        )
        x_values, y_values = _build_envelope_polygon(segment)
        result = WaveformRenderResult(x_values=x_values, y_values=y_values, segment=segment)

        if self.plot_item is not None and pg is not None:
            self._render_to_plot(result)
        return result

    def _render_to_plot(self, result: WaveformRenderResult) -> None:
        """Update the target pyqtgraph item with the visible waveform."""

        if self._upper_curve is None:
            pen = pg.mkPen(self.color, width=POLYGON_LINE_WIDTH)
            self._upper_curve = self.plot_item.plot(pen=pen)
            self._lower_curve = self.plot_item.plot(pen=pen)
            fill_brush = pg.mkBrush(self.color + f"{POLYGON_FILL_ALPHA:02x}")
            self._fill_item = pg.FillBetweenItem(self._upper_curve, self._lower_curve, brush=fill_brush)
            self.plot_item.addItem(self._fill_item)

        self._upper_curve.setData(result.segment.time_values, result.segment.max_values)
        self._lower_curve.setData(result.segment.time_values, result.segment.min_values)


def _build_envelope_polygon(segment: WaveformSegment) -> tuple[np.ndarray, np.ndarray]:
    """Build a closed polygon for filled waveform drawing."""

    x_values = np.concatenate([segment.time_values, segment.time_values[::-1]])
    y_values = np.concatenate([segment.max_values, segment.min_values[::-1]])
    return x_values, y_values
