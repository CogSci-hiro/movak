"""Viewport tests."""

from __future__ import annotations

from movak.timeline.viewport import TimelineViewport


def test_viewport_updates_pixels_per_second_on_zoom() -> None:
    """Zooming updates the visible duration and pixels-per-second."""

    viewport = TimelineViewport(
        visible_start_time=0.0,
        visible_end_time=10.0,
        pixels_per_second=100.0,
        total_duration=120.0,
    )

    viewport.zoom(2.0)

    assert viewport.visible_duration == 5.0
    assert viewport.pixels_per_second == 200.0


def test_viewport_scroll_clamps_to_total_duration() -> None:
    """Scrolling respects the recording duration."""

    viewport = TimelineViewport(
        visible_start_time=90.0,
        visible_end_time=100.0,
        pixels_per_second=80.0,
        total_duration=100.0,
    )

    viewport.scroll(10.0)

    assert viewport.visible_start_time == 90.0
    assert viewport.visible_end_time == 100.0


def test_viewport_converts_time_and_pixels() -> None:
    """Time and pixel conversions are consistent."""

    viewport = TimelineViewport(
        visible_start_time=5.0,
        visible_end_time=15.0,
        pixels_per_second=50.0,
    )

    assert viewport.time_to_pixel(7.0) == 100.0
    assert viewport.pixel_to_time(250.0) == 10.0
