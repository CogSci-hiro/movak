import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings

from movak.app.session_manager import SessionManager
from movak.gui.controllers.playback_controller import PlaybackController
from movak.gui.main_window import MainWindow


def test_main_window_restores_session_state_and_reopens_last_file(qtbot, monkeypatch, tmp_path):
    settings_path = tmp_path / "movak-session.ini"
    audio_path = tmp_path / "example.wav"
    audio_path.write_bytes(b"fake-audio")

    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    settings.setValue("session/last_opened_file", str(audio_path))
    settings.setValue("session/left_panel_visible", False)
    settings.setValue("session/right_panel_visible", True)
    settings.setValue("session/bottom_panel_visible", False)
    settings.setValue("session/active_left_pane", "review")
    settings.setValue("session/active_right_pane", "inspector")
    settings.setValue("view/loop_enabled", True)
    settings.setValue("view/waveform_display_mode", "stereo")
    settings.setValue("splitters/main", [46, 1100, 360])
    settings.setValue("splitters/center", [980, 0])
    settings.sync()

    opened_paths: list[str] = []

    def fake_open_audio_path(self: PlaybackController, selected_path: str) -> bool:
        opened_paths.append(selected_path)
        self.audio_file_loaded.emit(selected_path)
        return True

    monkeypatch.setattr(PlaybackController, "open_audio_path", fake_open_audio_path)

    session_manager = SessionManager(settings=settings)
    window = MainWindow(session_manager=session_manager)
    qtbot.addWidget(window)

    assert opened_paths == [str(audio_path)]
    assert window.active_left_pane_id is None
    assert window.active_right_pane_id == "inspector"
    assert window.is_bottom_panel_visible() is False
    assert window.timeline_panel.transport_bar.loop_button.isChecked() is True
    assert window.timeline_panel.transport_bar.current_waveform_display_mode() == "stereo"


def test_main_window_ignores_missing_last_file_on_restore(qtbot, monkeypatch, tmp_path):
    settings_path = tmp_path / "movak-missing-file.ini"
    missing_audio_path = tmp_path / "missing.wav"

    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    settings.setValue("session/last_opened_file", str(missing_audio_path))
    settings.sync()

    opened_paths: list[str] = []

    def fake_open_audio_path(self: PlaybackController, selected_path: str) -> bool:
        opened_paths.append(selected_path)
        self.audio_file_loaded.emit(selected_path)
        return True

    monkeypatch.setattr(PlaybackController, "open_audio_path", fake_open_audio_path)

    session_manager = SessionManager(settings=settings)
    window = MainWindow(session_manager=session_manager)
    qtbot.addWidget(window)

    assert opened_paths == []


def test_main_window_respects_reopen_last_audio_preference(qtbot, monkeypatch, tmp_path):
    settings_path = tmp_path / "movak-reopen-disabled.ini"
    audio_path = tmp_path / "example.wav"
    audio_path.write_bytes(b"fake-audio")

    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    settings.setValue("session/last_opened_file", str(audio_path))
    settings.setValue("preferences/reopen_last_audio_on_launch", False)
    settings.sync()

    opened_paths: list[str] = []

    def fake_open_audio_path(self: PlaybackController, selected_path: str) -> bool:
        opened_paths.append(selected_path)
        self.audio_file_loaded.emit(selected_path)
        return True

    monkeypatch.setattr(PlaybackController, "open_audio_path", fake_open_audio_path)

    session_manager = SessionManager(settings=settings)
    window = MainWindow(session_manager=session_manager)
    qtbot.addWidget(window)

    assert opened_paths == []
