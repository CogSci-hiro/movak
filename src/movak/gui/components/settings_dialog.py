from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget


class SettingsDialog(QDialog):
    """Small application settings dialog for global preferences."""

    def __init__(self, reopen_last_audio_on_launch: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(420, 180)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_label = QLabel("General", self)
        title_label.setObjectName("sectionLabel")
        layout.addWidget(title_label)

        self.reopen_last_audio_checkbox = QCheckBox("Reopen last audio file on launch", self)
        self.reopen_last_audio_checkbox.setChecked(reopen_last_audio_on_launch)
        layout.addWidget(self.reopen_last_audio_checkbox)

        hint_label = QLabel("More app preferences will live here as Movak grows.", self)
        hint_label.setWordWrap(True)
        hint_label.setTextFormat(Qt.TextFormat.PlainText)
        hint_label.setObjectName("statCaption")
        layout.addWidget(hint_label)

        layout.addStretch(1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def reopen_last_audio_on_launch(self) -> bool:
        """Return whether the last audio file should reopen on launch."""

        return self.reopen_last_audio_checkbox.isChecked()
