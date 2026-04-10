from movak.gui.timeline.scrollbar_sync import (
    scrollbar_value_to_time_range,
    visible_range_to_scrollbar_state,
)


def test_visible_range_to_scrollbar_state_disables_scrollbar_for_full_view():
    state = visible_range_to_scrollbar_state(
        total_duration_s=12.0,
        visible_start_s=0.0,
        visible_end_s=12.0,
    )

    assert state.minimum == 0
    assert state.maximum == 0
    assert state.page_step == 12_000
    assert state.single_step == 1_200
    assert state.value == 0
    assert state.enabled is False
    assert state.visible is False


def test_visible_range_to_scrollbar_state_tracks_zoomed_window():
    state = visible_range_to_scrollbar_state(
        total_duration_s=12.0,
        visible_start_s=3.5,
        visible_end_s=6.0,
    )

    assert state.maximum == 9_500
    assert state.page_step == 2_500
    assert state.single_step == 250
    assert state.value == 3_500
    assert state.enabled is True
    assert state.visible is True


def test_scrollbar_value_to_time_range_preserves_window_width():
    start_time_s, end_time_s = scrollbar_value_to_time_range(
        total_duration_s=12.0,
        visible_duration_s=2.5,
        start_value=3_500,
    )

    assert start_time_s == 3.5
    assert end_time_s == 6.0


def test_scrollbar_value_to_time_range_clamps_at_end():
    start_time_s, end_time_s = scrollbar_value_to_time_range(
        total_duration_s=12.0,
        visible_duration_s=2.5,
        start_value=11_500,
    )

    assert start_time_s == 9.5
    assert end_time_s == 12.0


def test_visible_range_to_scrollbar_state_shows_scrollbar_for_sub_millisecond_zoom():
    state = visible_range_to_scrollbar_state(
        total_duration_s=12.0,
        visible_start_s=0.0,
        visible_end_s=11.9995,
    )

    assert state.enabled is True
    assert state.visible is True
