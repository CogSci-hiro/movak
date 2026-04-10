from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QSize

from ..style.spacing import Spacing


@dataclass(frozen=True, slots=True)
class LeftPaneSpec:
    pane_id: str
    tooltip: str
    icon: QIcon
    widget: QWidget


class _UtilityToolButton(QToolButton):
    def __init__(self, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("utilityToolButton")
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRaise(True)
        self.setFixedSize(34, 34)
        self.setIconSize(QSize(16, 16))


class LeftToolBar(QFrame):
    pane_requested = pyqtSignal(str)
    bottom_tool_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftUtilityBar")
        self._buttons: dict[str, QToolButton] = {}
        self._bottom_buttons: dict[str, QToolButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XS, Spacing.LG, Spacing.XS, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        self._top_button_group = QButtonGroup(self)
        self._top_button_group.setExclusive(False)
        self._bottom_button_group = QButtonGroup(self)
        self._bottom_button_group.setExclusive(False)

        self._top_layout = QVBoxLayout()
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(Spacing.XS)
        layout.addLayout(self._top_layout)
        layout.addStretch(1)

        self._bottom_layout = QVBoxLayout()
        self._bottom_layout.setContentsMargins(0, 0, 0, 0)
        self._bottom_layout.setSpacing(Spacing.XS)
        layout.addLayout(self._bottom_layout)

        self.setFixedWidth(46)

    def add_pane(self, pane_id: str, icon, tooltip: str) -> None:
        self._add_button(
            target_id=pane_id,
            icon=icon,
            tooltip=tooltip,
            button_group=self._top_button_group,
            button_map=self._buttons,
            target_layout=self._top_layout,
            emit_requested=self.pane_requested.emit,
        )

    def add_bottom_tool(self, tool_id: str, icon: QIcon, tooltip: str) -> None:
        self._add_button(
            target_id=tool_id,
            icon=icon,
            tooltip=tooltip,
            button_group=self._bottom_button_group,
            button_map=self._bottom_buttons,
            target_layout=self._bottom_layout,
            emit_requested=self.bottom_tool_requested.emit,
        )

    def set_active_pane(self, pane_id: str | None) -> None:
        self._set_checked_button(self._buttons, pane_id)

    def set_active_bottom_tool(self, tool_id: str | None) -> None:
        self._set_checked_button(self._bottom_buttons, tool_id)

    def _add_button(
        self,
        target_id: str,
        icon: QIcon,
        tooltip: str,
        button_group: QButtonGroup,
        button_map: dict[str, QToolButton],
        target_layout: QVBoxLayout,
        emit_requested: Callable[[str], None],
    ) -> None:
        button = _UtilityToolButton(tooltip, self)
        button.setIcon(icon)
        button.clicked.connect(lambda checked=False, requested_id=target_id: emit_requested(requested_id))
        button_group.addButton(button)
        button_map[target_id] = button
        target_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)

    def _set_checked_button(self, button_map: dict[str, QToolButton], active_id: str | None) -> None:
        for candidate_id, button in button_map.items():
            button.blockSignals(True)
            button.setChecked(candidate_id == active_id)
            button.blockSignals(False)


class LeftPaneContainer(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftPaneContainer")
        self._pane_widgets: dict[str, QWidget] = {}
        self._current_pane_id: str | None = None
        self._expanded_width = 268

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("leftPaneStack")
        layout.addWidget(self.stack)

        self.setMinimumWidth(0)
        self.setMaximumWidth(0)
        self.hide()

    @property
    def expanded_width(self) -> int:
        return self._expanded_width

    def set_expanded_width(self, width: int) -> None:
        self._expanded_width = max(220, width)

    def add_pane(self, pane_id: str, widget: QWidget) -> None:
        self._pane_widgets[pane_id] = widget
        self.stack.addWidget(widget)

    def show_pane(self, pane_id: str) -> None:
        widget = self._pane_widgets[pane_id]
        self._current_pane_id = pane_id
        self.stack.setCurrentWidget(widget)
        self.setMinimumWidth(self._expanded_width)
        self.setMaximumWidth(420)
        self.show()

    def collapse(self) -> None:
        self._current_pane_id = None
        self.hide()
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)

    def current_pane_id(self) -> str | None:
        return self._current_pane_id


class LeftDock(QWidget):
    pane_requested = pyqtSignal(str)
    bottom_tool_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftDock")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.tool_bar = LeftToolBar(self)
        self.pane_container = LeftPaneContainer(self)

        self.tool_bar.pane_requested.connect(self.pane_requested.emit)
        self.tool_bar.bottom_tool_requested.connect(self.bottom_tool_requested.emit)

        layout.addWidget(self.tool_bar, 0)
        layout.addWidget(self.pane_container, 1)

    def add_pane(self, spec: LeftPaneSpec) -> None:
        self.tool_bar.add_pane(spec.pane_id, spec.icon, spec.tooltip)
        self.pane_container.add_pane(spec.pane_id, spec.widget)

    def add_bottom_tool(self, tool_id: str, icon: QIcon, tooltip: str) -> None:
        self.tool_bar.add_bottom_tool(tool_id, icon, tooltip)

    def set_active_pane(self, pane_id: str | None) -> None:
        self.tool_bar.set_active_pane(pane_id)
        if pane_id is None:
            self.pane_container.collapse()
        else:
            self.pane_container.show_pane(pane_id)

    def set_active_bottom_tool(self, tool_id: str | None) -> None:
        self.tool_bar.set_active_bottom_tool(tool_id)

    def pane_width(self) -> int:
        if not self.pane_container.isVisible():
            return 0
        return max(self.pane_container.width(), self.pane_container.expanded_width)
