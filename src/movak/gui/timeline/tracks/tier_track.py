from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pyqtgraph as pg
from PyQt6.QtGui import QPainterPath
from PyQt6.QtWidgets import QGraphicsPathItem

from ...style.palette import Palette
from ..timeline_track import TimelineTrack

TIER_DEFAULT_HEIGHT = 84
TIER_INTERVAL_TOP = 0.18
TIER_INTERVAL_HEIGHT = 0.58
TIER_CORNER_RADIUS = 0.03
TIER_TEXT_Y = 0.47


@dataclass(slots=True)
class TierInterval:
    """Interval metadata rendered by a tier track.

    Parameters
    ----------
    start
        Interval start time in seconds.
    end
        Interval end time in seconds.
    label
        Display label shown inside the interval box.
    """

    start: float
    end: float
    label: str


class TierTrack(TimelineTrack):
    """Annotation tier rendered as rounded interval blocks.

    Parameters
    ----------
    tier_name
        Human-readable tier name.
    intervals
        Intervals belonging to the tier.
    parent
        Optional parent widget.
    """

    def __init__(
        self,
        tier_name: str,
        intervals: Iterable[TierInterval] | None = None,
        parent=None,
    ) -> None:
        super().__init__(tier_name, parent)
        self.intervals = sorted(list(intervals or _build_placeholder_intervals(tier_name)), key=lambda item: item.start)
        self.plot_widget.setYRange(0.0, 1.0, padding=0.0)
        self.setMinimumHeight(TIER_DEFAULT_HEIGHT)
        self._items: list[object] = []

    def render(self, start_time: float, end_time: float) -> None:
        """Render only intervals overlapping the visible window."""

        self._clear_items()
        for interval in self._visible_intervals(start_time, end_time):
            path = QPainterPath()
            width = interval.end - interval.start
            path.addRoundedRect(
                interval.start,
                TIER_INTERVAL_TOP,
                width,
                TIER_INTERVAL_HEIGHT,
                TIER_CORNER_RADIUS,
                TIER_CORNER_RADIUS,
            )

            box_item = QGraphicsPathItem(path)
            box_item.setPen(pg.mkPen(Palette.BORDER, width=1))
            box_item.setBrush(pg.mkBrush(Palette.ACCENT_STRONG if self.track_name.lower().startswith("word") else Palette.ACCENT_VIOLET_SOFT))
            self.plot_widget.addItem(box_item)
            self._items.append(box_item)

            label_item = pg.TextItem(interval.label, color=Palette.TEXT, anchor=(0.5, 0.5))
            label_item.setPos(interval.start + (width / 2.0), TIER_TEXT_Y)
            self.plot_widget.addItem(label_item)
            self._items.append(label_item)

    def _visible_intervals(self, start_time: float, end_time: float) -> list[TierInterval]:
        """Return intervals overlapping the current visible range."""

        return [
            interval
            for interval in self.intervals
            if interval.start < end_time and start_time < interval.end
        ]

    def _clear_items(self) -> None:
        """Remove previously rendered items before repainting the track."""

        for item in self._items:
            self.plot_widget.removeItem(item)
        self._items.clear()


def _build_placeholder_intervals(tier_name: str) -> list[TierInterval]:
    """Return sample intervals for empty demo states."""

    if tier_name.lower().startswith("word"):
        return [
            TierInterval(0.20, 1.60, "hello"),
            TierInterval(1.75, 3.10, "world"),
            TierInterval(3.35, 4.75, "today"),
        ]
    return [
        TierInterval(0.20, 0.52, "h"),
        TierInterval(0.52, 0.88, "e"),
        TierInterval(0.88, 1.20, "l"),
        TierInterval(1.20, 1.60, "o"),
        TierInterval(1.75, 2.10, "w"),
        TierInterval(2.10, 2.45, "ɜ"),
        TierInterval(2.45, 2.78, "l"),
        TierInterval(2.78, 3.10, "d"),
    ]
