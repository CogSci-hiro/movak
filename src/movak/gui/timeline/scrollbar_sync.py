from __future__ import annotations

from dataclasses import dataclass

SCROLLBAR_TIME_SCALE = 1_000
FULL_VIEW_TOLERANCE_SECONDS = 1e-6


@dataclass(slots=True)
class ScrollbarState:
    """Horizontal scrollbar state derived from a visible time range."""

    minimum: int
    maximum: int
    page_step: int
    single_step: int
    value: int
    enabled: bool
    visible: bool


def visible_range_to_scrollbar_state(
    *,
    total_duration_s: float,
    visible_start_s: float,
    visible_end_s: float,
) -> ScrollbarState:
    """Convert a visible time range into horizontal scrollbar semantics."""
    clamped_total_duration_s = max(0.0, total_duration_s)
    visible_width_s = max(0.0, visible_end_s - visible_start_s)

    total_duration_ms = max(1, round(clamped_total_duration_s * SCROLLBAR_TIME_SCALE))
    visible_width_ms = max(1, round(visible_width_s * SCROLLBAR_TIME_SCALE))
    start_value = max(0, round(visible_start_s * SCROLLBAR_TIME_SCALE))
    maximum = max(0, total_duration_ms - visible_width_ms)
    value = min(start_value, maximum)
    full_visible = (clamped_total_duration_s - visible_width_s) <= FULL_VIEW_TOLERANCE_SECONDS
    return ScrollbarState(
        minimum=0,
        maximum=maximum,
        page_step=visible_width_ms,
        single_step=max(1, visible_width_ms // 10),
        value=value,
        enabled=not full_visible,
        visible=not full_visible,
    )


def scrollbar_value_to_time_range(
    *,
    total_duration_s: float,
    visible_duration_s: float,
    start_value: int,
) -> tuple[float, float]:
    """Convert a scrollbar value into a visible time range."""
    start_time_s = max(0.0, start_value / SCROLLBAR_TIME_SCALE)
    end_time_s = start_time_s + visible_duration_s
    if end_time_s > total_duration_s:
        end_time_s = total_duration_s
        start_time_s = max(0.0, end_time_s - visible_duration_s)
    return start_time_s, end_time_s
