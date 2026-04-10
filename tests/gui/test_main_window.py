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
