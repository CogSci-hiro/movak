import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QLabel

from movak.gui.components.left_dock import LeftDock, LeftPaneSpec


def test_left_dock_can_toggle_and_switch_panes():
    app = QApplication.instance() or QApplication([])
    dock = LeftDock()
    dock.show()
    app.processEvents()

    dock.add_pane(LeftPaneSpec("corpus", "Project", QIcon(), QLabel("Corpus")))
    dock.add_pane(LeftPaneSpec("search", "Search", QIcon(), QLabel("Search")))

    dock.set_active_pane("corpus")
    app.processEvents()
    assert dock.pane_container.isVisible()
    assert dock.pane_container.current_pane_id() == "corpus"
    assert dock.tool_bar._buttons["corpus"].isChecked()

    dock.set_active_pane(None)
    app.processEvents()
    assert not dock.pane_container.isVisible()
    assert dock.pane_container.current_pane_id() is None
    assert not dock.tool_bar._buttons["corpus"].isChecked()

    dock.set_active_pane("search")
    app.processEvents()
    assert dock.pane_container.isVisible()
    assert dock.pane_container.current_pane_id() == "search"
    assert dock.tool_bar._buttons["search"].isChecked()
    assert not dock.tool_bar._buttons["corpus"].isChecked()

    dock.close()


def test_left_dock_bottom_tools_track_independent_active_state():
    app = QApplication.instance() or QApplication([])
    dock = LeftDock()
    dock.show()
    app.processEvents()

    dock.add_pane(LeftPaneSpec("corpus", "Project", QIcon(), QLabel("Corpus")))
    dock.add_bottom_tool("review_panel", QIcon(), "Review")

    dock.set_active_pane("corpus")
    dock.set_active_bottom_tool("review_panel")
    app.processEvents()

    assert dock.tool_bar._buttons["corpus"].isChecked()
    assert dock.tool_bar._bottom_buttons["review_panel"].isChecked()

    dock.set_active_bottom_tool(None)
    app.processEvents()

    assert dock.tool_bar._buttons["corpus"].isChecked()
    assert not dock.tool_bar._bottom_buttons["review_panel"].isChecked()

    dock.close()
