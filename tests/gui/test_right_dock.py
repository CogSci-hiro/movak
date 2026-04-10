import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QLabel

from movak.gui.components.right_dock import RightDock, RightPaneSpec


def test_right_dock_can_toggle_and_switch_panes():
    app = QApplication.instance() or QApplication([])
    dock = RightDock()
    dock.show()
    app.processEvents()

    dock.add_pane(RightPaneSpec("analysis", "Analysis", QIcon(), QLabel("Analysis")))
    dock.add_pane(RightPaneSpec("inspector", "Inspector", QIcon(), QLabel("Inspector")))

    dock.set_active_pane("analysis")
    app.processEvents()
    assert dock.pane_container.isVisible()
    assert dock.pane_container.current_pane_id() == "analysis"
    assert dock.tool_bar._buttons["analysis"].isChecked()

    dock.set_active_pane(None)
    app.processEvents()
    assert not dock.pane_container.isVisible()
    assert dock.pane_container.current_pane_id() is None
    assert not dock.tool_bar._buttons["analysis"].isChecked()

    dock.set_active_pane("inspector")
    app.processEvents()
    assert dock.pane_container.isVisible()
    assert dock.pane_container.current_pane_id() == "inspector"
    assert dock.tool_bar._buttons["inspector"].isChecked()
    assert not dock.tool_bar._buttons["analysis"].isChecked()

    dock.close()
