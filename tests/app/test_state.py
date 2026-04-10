import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from movak.app.state import AppState, deserialize_app_state, serialize_app_state


def test_app_state_serialization_round_trips_expected_values():
    state = AppState(
        last_opened_file="/tmp/example.wav",
        left_panel_visible=False,
        right_panel_visible=True,
        bottom_panel_visible=False,
        active_left_pane_id=None,
        active_right_pane_id="inspector",
        loop_enabled=True,
        waveform_display_mode="stereo",
        shell_splitter_sizes=(50, 1000, 320),
        content_splitter_sizes=(950, 0),
        left_panel_width=280,
        right_panel_width=340,
    )

    serialized_values = serialize_app_state(state)
    restored_state = deserialize_app_state(serialized_values)

    assert restored_state == state


def test_app_state_deserialization_falls_back_safely_for_invalid_values():
    restored_state = deserialize_app_state(
        {
            "session/last_opened_file": "  ",
            "session/left_panel_visible": "maybe",
            "session/right_panel_visible": "0",
            "session/bottom_panel_visible": "1",
            "session/active_left_pane": "",
            "session/active_right_pane": " ",
            "session/left_panel_width": "wide",
            "session/right_panel_width": "320",
            "view/loop_enabled": "yes",
            "view/waveform_display_mode": "unknown",
            "splitters/main": ["314", "bad", "360"],
            "splitters/center": "800,not-a-number",
        }
    )

    assert restored_state.last_opened_file is None
    assert restored_state.left_panel_visible is True
    assert restored_state.right_panel_visible is False
    assert restored_state.bottom_panel_visible is True
    assert restored_state.active_left_pane_id == "corpus"
    assert restored_state.active_right_pane_id is None
    assert restored_state.left_panel_width is None
    assert restored_state.right_panel_width == 320
    assert restored_state.loop_enabled is True
    assert restored_state.waveform_display_mode == "mono"
    assert restored_state.shell_splitter_sizes == (314, 926, 360)
    assert restored_state.content_splitter_sizes == (720, 230)
