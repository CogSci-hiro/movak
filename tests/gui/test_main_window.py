from PyQt6.QtWidgets import QApplication
from movak.gui.main_window import MainWindow


def test_window_creation(qtbot):
    window = MainWindow()

    qtbot.addWidget(window)

    assert window is not None
