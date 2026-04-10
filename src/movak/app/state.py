"""Application persistence state models and serialization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PyQt6.QtCore import QByteArray

DEFAULT_LEFT_PANEL_ID = "corpus"
DEFAULT_RIGHT_PANEL_ID = "analysis"
DEFAULT_WAVEFORM_DISPLAY_MODE = "mono"
DEFAULT_SHELL_SPLITTER_SIZES = (314, 926, 360)
DEFAULT_CONTENT_SPLITTER_SIZES = (720, 230)


@dataclass(slots=True)
class AppState:
    """Persisted session and UI state for the main window.

    Parameters
    ----------
    last_opened_file:
        Absolute path to the most recently opened audio file.
    left_panel_visible:
        Whether the left utility pane is expanded.
    right_panel_visible:
        Whether the right utility pane is expanded.
    bottom_panel_visible:
        Whether the bottom review panel is visible.
    active_left_pane_id:
        Currently selected left pane identifier when visible.
    active_right_pane_id:
        Currently selected right pane identifier when visible.
    loop_enabled:
        Whether the loop button is checked.
    waveform_display_mode:
        Current waveform display mode selection.
    shell_splitter_sizes:
        Horizontal shell splitter sizes.
    content_splitter_sizes:
        Vertical content splitter sizes.
    left_panel_width:
        Expanded width remembered for the left pane container.
    right_panel_width:
        Expanded width remembered for the right pane container.
    main_window_geometry:
        Serialized main window geometry from Qt.
    main_window_state:
        Serialized main window state from Qt.
    """

    last_opened_file: str | None = None
    left_panel_visible: bool = True
    right_panel_visible: bool = True
    bottom_panel_visible: bool = True
    active_left_pane_id: str | None = DEFAULT_LEFT_PANEL_ID
    active_right_pane_id: str | None = DEFAULT_RIGHT_PANEL_ID
    loop_enabled: bool = False
    waveform_display_mode: str = DEFAULT_WAVEFORM_DISPLAY_MODE
    shell_splitter_sizes: tuple[int, int, int] = DEFAULT_SHELL_SPLITTER_SIZES
    content_splitter_sizes: tuple[int, int] = DEFAULT_CONTENT_SPLITTER_SIZES
    left_panel_width: int | None = None
    right_panel_width: int | None = None
    main_window_geometry: QByteArray | None = None
    main_window_state: QByteArray | None = None


def serialize_app_state(state: AppState) -> dict[str, object]:
    """Convert an :class:`AppState` into QSettings-friendly values.

    Parameters
    ----------
    state:
        State instance to serialize.

    Returns
    -------
    dict[str, object]
        Mapping of stable settings keys to Qt-storable values.
    """

    return {
        "main_window/geometry": state.main_window_geometry,
        "main_window/window_state": state.main_window_state,
        "session/last_opened_file": state.last_opened_file or "",
        "session/left_panel_visible": state.left_panel_visible,
        "session/right_panel_visible": state.right_panel_visible,
        "session/bottom_panel_visible": state.bottom_panel_visible,
        "session/active_left_pane": state.active_left_pane_id or "",
        "session/active_right_pane": state.active_right_pane_id or "",
        "session/left_panel_width": state.left_panel_width,
        "session/right_panel_width": state.right_panel_width,
        "view/loop_enabled": state.loop_enabled,
        "view/waveform_display_mode": state.waveform_display_mode,
        "splitters/main": list(state.shell_splitter_sizes),
        "splitters/center": list(state.content_splitter_sizes),
    }


def deserialize_app_state(values: Mapping[str, Any]) -> AppState:
    """Build an :class:`AppState` from QSettings-like values.

    Parameters
    ----------
    values:
        Mapping containing persisted key-value pairs.

    Returns
    -------
    AppState
        Parsed application state with safe defaults.
    """

    left_panel_visible = _read_bool(values.get("session/left_panel_visible"), True)
    right_panel_visible = _read_bool(values.get("session/right_panel_visible"), True)
    active_left_pane_id = _read_optional_string(values.get("session/active_left_pane"))
    active_right_pane_id = _read_optional_string(values.get("session/active_right_pane"))

    if left_panel_visible and active_left_pane_id is None:
        active_left_pane_id = DEFAULT_LEFT_PANEL_ID
    if right_panel_visible and active_right_pane_id is None:
        active_right_pane_id = DEFAULT_RIGHT_PANEL_ID

    return AppState(
        last_opened_file=_read_optional_string(values.get("session/last_opened_file")),
        left_panel_visible=left_panel_visible,
        right_panel_visible=right_panel_visible,
        bottom_panel_visible=_read_bool(values.get("session/bottom_panel_visible"), True),
        active_left_pane_id=active_left_pane_id,
        active_right_pane_id=active_right_pane_id,
        loop_enabled=_read_bool(values.get("view/loop_enabled"), False),
        waveform_display_mode=_read_waveform_mode(values.get("view/waveform_display_mode")),
        shell_splitter_sizes=_read_sizes(values.get("splitters/main"), 3, DEFAULT_SHELL_SPLITTER_SIZES),
        content_splitter_sizes=_read_sizes(values.get("splitters/center"), 2, DEFAULT_CONTENT_SPLITTER_SIZES),
        left_panel_width=_read_optional_int(values.get("session/left_panel_width")),
        right_panel_width=_read_optional_int(values.get("session/right_panel_width")),
        main_window_geometry=_read_byte_array(values.get("main_window/geometry")),
        main_window_state=_read_byte_array(values.get("main_window/window_state")),
    )


def _read_bool(value: Any, fallback: bool) -> bool:
    """Parse a settings value as a boolean."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value in {"1", "true", "yes", "on"}:
            return True
        if normalized_value in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, int):
        return bool(value)
    return fallback


def _read_optional_string(value: Any, fallback: str | None = None) -> str | None:
    """Parse a settings value as an optional string."""

    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _read_optional_int(value: Any) -> int | None:
    """Parse a settings value as an optional integer."""

    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_sizes(value: Any, expected_length: int, fallback: tuple[int, ...]) -> tuple[int, ...]:
    """Parse persisted splitter sizes with length validation."""

    if isinstance(value, (list, tuple)):
        raw_values = value
    elif isinstance(value, str):
        raw_values = [chunk.strip() for chunk in value.split(",")]
    else:
        return fallback

    if len(raw_values) != expected_length:
        return fallback

    parsed_values: list[int] = []
    for raw_value in raw_values:
        try:
            parsed_values.append(int(raw_value))
        except (TypeError, ValueError):
            return fallback
    return tuple(parsed_values)


def _read_byte_array(value: Any) -> QByteArray | None:
    """Normalize persisted Qt byte-array values."""

    if isinstance(value, QByteArray):
        return value if not value.isEmpty() else None
    if isinstance(value, (bytes, bytearray)):
        byte_array = QByteArray(bytes(value))
        return byte_array if not byte_array.isEmpty() else None
    return None


def _read_waveform_mode(value: Any) -> str:
    """Parse the waveform display mode."""

    if str(value).strip().lower() == "stereo":
        return "stereo"
    return DEFAULT_WAVEFORM_DISPLAY_MODE
