from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QStyle, QToolButton, QWidget

from ..style.spacing import Spacing

DEFAULT_POSITION_TEXT = "00:00"
DEFAULT_SOURCE_TEXT = "No audio loaded"
PLAY_BUTTON_WIDTH = 76
MONO_MODE = "mono"
STEREO_MODE = "stereo"


class TransportBar(QFrame):
    """Bottom-attached transport controls for the central editor pane."""

    open_requested = pyqtSignal()
    play_pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    fit_requested = pyqtSignal()
    center_on_playhead_requested = pyqtSignal()
    waveform_display_mode_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("transportBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        self.open_button = QPushButton("Open Audio", self)
        self.open_button.setObjectName("ghostButton")

        self.rewind_button = self._make_button(QStyle.StandardPixmap.SP_MediaSeekBackward, "Step back")
        self.play_button = self._make_button(QStyle.StandardPixmap.SP_MediaPlay, "Play")
        self.play_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.play_button.setFixedSize(PLAY_BUTTON_WIDTH, 30)
        self.stop_button = self._make_button(QStyle.StandardPixmap.SP_MediaStop, "Stop")
        self.forward_button = self._make_button(QStyle.StandardPixmap.SP_MediaSeekForward, "Step forward")
        self.loop_button = QPushButton("Loop", self)
        self.loop_button.setObjectName("ghostButton")
        self.loop_button.setCheckable(True)

        self.position_label = QLabel(DEFAULT_POSITION_TEXT, self)
        self.position_label.setObjectName("sectionLabel")
        self.duration_label = QLabel(DEFAULT_POSITION_TEXT, self)
        self.duration_label.setObjectName("sectionLabel")
        self.source_label = QLabel(DEFAULT_SOURCE_TEXT, self)
        self.source_label.setObjectName("statCaption")

        self.rate_label = QLabel("Speed", self)
        self.rate_label.setObjectName("statCaption")
        self.rate_combo = QComboBox(self)
        self.rate_combo.addItems(["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.rate_combo.setCurrentText("1.0x")
        self.rate_combo.setEnabled(False)

        self.waveform_mode_label = QLabel("Waveform", self)
        self.waveform_mode_label.setObjectName("statCaption")
        self.waveform_mode_combo = QComboBox(self)
        self.waveform_mode_combo.addItem("Mono", userData=MONO_MODE)
        self.waveform_mode_combo.addItem("Stereo", userData=STEREO_MODE)
        self.waveform_mode_combo.setCurrentIndex(0)
        self.waveform_mode_combo.setEnabled(False)

        self.focus_button = QPushButton(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward),
            "Center",
            self,
        )
        self.focus_button.setObjectName("ghostButton")
        self.fit_button = QPushButton("Fit", self)
        self.fit_button.setObjectName("ghostButton")

        layout.addWidget(self.open_button)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.rewind_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.forward_button)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.loop_button)
        layout.addSpacing(Spacing.MD)
        layout.addWidget(self.position_label)
        layout.addWidget(QLabel("/", self))
        layout.addWidget(self.duration_label)
        layout.addWidget(self.source_label)
        layout.addStretch(1)
        layout.addWidget(self.waveform_mode_label)
        layout.addWidget(self.waveform_mode_combo)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.rate_label)
        layout.addWidget(self.rate_combo)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.fit_button)
        layout.addWidget(self.focus_button)

        self.open_button.clicked.connect(self.open_requested.emit)
        self.play_button.clicked.connect(self.play_pause_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.fit_button.clicked.connect(self.fit_requested.emit)
        self.focus_button.clicked.connect(self.center_on_playhead_requested.emit)
        self.waveform_mode_combo.currentIndexChanged.connect(self._emit_waveform_mode_changed)

        self.set_is_playing(False)

    def _make_button(self, icon_type: QStyle.StandardPixmap, tooltip: str) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("transportButton")
        button.setIcon(self.style().standardIcon(icon_type))
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAutoRaise(True)
        button.setFixedSize(30, 30)
        button.setIconSize(button.iconSize())
        return button

    def set_source_label(self, text: str) -> None:
        """Update the current source label."""
        self.source_label.setText(text)

    def set_position_text(self, text: str) -> None:
        """Update the current playback position label."""
        self.position_label.setText(text)

    def set_duration_text(self, text: str) -> None:
        """Update the media duration label."""
        self.duration_label.setText(text)

    def set_is_playing(self, is_playing: bool) -> None:
        """Update the play button to match the current playback state."""
        icon_type = QStyle.StandardPixmap.SP_MediaPause if is_playing else QStyle.StandardPixmap.SP_MediaPlay
        self.play_button.setIcon(self.style().standardIcon(icon_type))
        self.play_button.setText("Pause" if is_playing else "Play")
        self.play_button.setToolTip("Pause" if is_playing else "Play")

    def set_waveform_mode_availability(self, stereo_available: bool) -> None:
        """Enable stereo mode when the loaded audio has at least two channels."""
        self.waveform_mode_combo.setEnabled(stereo_available)
        if not stereo_available:
            self.set_waveform_display_mode(MONO_MODE)

    def set_waveform_display_mode(self, mode: str) -> None:
        """Set the selected waveform display mode."""
        wanted_mode = STEREO_MODE if mode == STEREO_MODE else MONO_MODE
        current_mode = self.current_waveform_display_mode()
        if current_mode == wanted_mode:
            return
        blocker = QSignalBlocker(self.waveform_mode_combo)
        index = self.waveform_mode_combo.findData(wanted_mode)
        self.waveform_mode_combo.setCurrentIndex(index if index >= 0 else 0)
        del blocker

    def current_waveform_display_mode(self) -> str:
        """Return selected waveform display mode."""
        selected_mode = self.waveform_mode_combo.currentData()
        return selected_mode if selected_mode in {MONO_MODE, STEREO_MODE} else MONO_MODE

    def _emit_waveform_mode_changed(self) -> None:
        self.waveform_display_mode_requested.emit(self.current_waveform_display_mode())
