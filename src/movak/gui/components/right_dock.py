from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..style.spacing import Spacing


@dataclass(frozen=True, slots=True)
class RightPaneSpec:
    pane_id: str
    tooltip: str
    icon: QIcon
    widget: QWidget


class _RightUtilityToolButton(QToolButton):
    def __init__(self, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightUtilityToolButton")
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRaise(True)
        self.setFixedSize(34, 34)
        self.setIconSize(QSize(16, 16))


class RightToolBar(QFrame):
    pane_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightUtilityBar")
        self._buttons: dict[str, QToolButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XS, Spacing.LG, Spacing.XS, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(False)

        self._top_layout = QVBoxLayout()
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(Spacing.XS)
        layout.addLayout(self._top_layout)
        layout.addStretch(1)

        self.setFixedWidth(46)

    def add_pane(self, pane_id: str, icon: QIcon, tooltip: str) -> None:
        button = _RightUtilityToolButton(tooltip, self)
        button.setIcon(icon)
        button.clicked.connect(lambda checked=False, target=pane_id: self.pane_requested.emit(target))
        self._button_group.addButton(button)
        self._buttons[pane_id] = button
        self._top_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)

    def set_active_pane(self, pane_id: str | None) -> None:
        for candidate_id, button in self._buttons.items():
            button.blockSignals(True)
            button.setChecked(candidate_id == pane_id)
            button.blockSignals(False)


class RightPaneContainer(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightPaneContainer")
        self._pane_widgets: dict[str, QWidget] = {}
        self._current_pane_id: str | None = None
        self._expanded_width = 320

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("rightPaneStack")
        layout.addWidget(self.stack)

        self.setMinimumWidth(0)
        self.setMaximumWidth(0)
        self.hide()

    @property
    def expanded_width(self) -> int:
        return self._expanded_width

    def set_expanded_width(self, width: int) -> None:
        self._expanded_width = max(260, width)

    def add_pane(self, pane_id: str, widget: QWidget) -> None:
        self._pane_widgets[pane_id] = widget
        self.stack.addWidget(widget)

    def show_pane(self, pane_id: str) -> None:
        widget = self._pane_widgets[pane_id]
        self._current_pane_id = pane_id
        self.stack.setCurrentWidget(widget)
        self.setMinimumWidth(self._expanded_width)
        self.setMaximumWidth(460)
        self.show()

    def collapse(self) -> None:
        self._current_pane_id = None
        self.hide()
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)

    def current_pane_id(self) -> str | None:
        return self._current_pane_id


class RightDock(QWidget):
    pane_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightDock")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.pane_container = RightPaneContainer(self)
        self.tool_bar = RightToolBar(self)

        self.tool_bar.pane_requested.connect(self.pane_requested.emit)

        layout.addWidget(self.pane_container, 1)
        layout.addWidget(self.tool_bar, 0)

    def add_pane(self, spec: RightPaneSpec) -> None:
        self.pane_container.add_pane(spec.pane_id, spec.widget)
        self.tool_bar.add_pane(spec.pane_id, spec.icon, spec.tooltip)

    def set_active_pane(self, pane_id: str | None) -> None:
        self.tool_bar.set_active_pane(pane_id)
        if pane_id is None:
            self.pane_container.collapse()
        else:
            self.pane_container.show_pane(pane_id)
