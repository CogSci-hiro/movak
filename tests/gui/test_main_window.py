from PyQt6.QtCore import Qt

from movak.gui.main_window import MainWindow


def test_window_creation(qtbot):
    window = MainWindow()

    qtbot.addWidget(window)

    assert window is not None


def test_bottom_toolbar_button_toggles_and_stays_in_sync(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(0)

    bottom_button = window.left_dock.tool_bar._bottom_buttons[window.DEFAULT_BOTTOM_TOOL_ID]

    window.set_bottom_panel_visible(True)
    assert window.is_bottom_panel_visible() is True
    assert bottom_button.isChecked() is True

    qtbot.mouseClick(bottom_button, Qt.MouseButton.LeftButton)
    assert window.is_bottom_panel_visible() is False
    assert bottom_button.isChecked() is False

    qtbot.mouseClick(bottom_button, Qt.MouseButton.LeftButton)
    assert window.is_bottom_panel_visible() is True
    assert bottom_button.isChecked() is True

    window.set_bottom_panel_visible(False)
    assert bottom_button.isChecked() is False

    window.set_bottom_panel_visible(True)
    assert bottom_button.isChecked() is True


def test_settings_action_opens_dialog_and_saves_preference(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    captured = {}

    class FakeSettingsDialog:
        DialogCode = type("DialogCode", (), {"Accepted": 1})

        def __init__(self, reopen_last_audio_on_launch: bool, parent=None) -> None:
            captured["initial_value"] = reopen_last_audio_on_launch
            captured["parent"] = parent

        def exec(self) -> int:
            captured["opened"] = True
            return self.DialogCode.Accepted

        def reopen_last_audio_on_launch(self) -> bool:
            return False

    monkeypatch.setattr("movak.gui.main_window.SettingsDialog", FakeSettingsDialog)

    window.settings_action.trigger()

    assert captured["opened"] is True
    assert captured["initial_value"] is True
    assert captured["parent"] is window
    assert window.session_manager.reopen_last_audio_on_launch() is False
