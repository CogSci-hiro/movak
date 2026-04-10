from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...audio.spectrogram import (
    PRAAT_DEFAULT_DYNAMIC_RANGE_DB,
    PRAAT_DEFAULT_MAX_FREQUENCY_HZ,
    PRAAT_DEFAULT_PREEMPHASIS_FROM_HZ,
    PRAAT_DEFAULT_TIME_STEP_S,
    PRAAT_DEFAULT_WINDOW_LENGTH_S,
    SpectrogramSettings,
)


class SpectrogramSettingsDialog(QDialog):
    """Modal editor for spectrogram analysis settings."""

    def __init__(self, settings: SpectrogramSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Spectrogram Settings")
        self.setModal(True)
        self.resize(360, 220)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.window_length_spin = _build_spin_box(1.0, 100.0, suffix=" ms", decimals=1)
        self.window_length_spin.setValue(settings.window_length_s * 1_000.0)
        form_layout.addRow("Window Length", self.window_length_spin)

        self.time_step_spin = _build_spin_box(0.5, 50.0, suffix=" ms", decimals=1)
        self.time_step_spin.setValue(settings.time_step_s * 1_000.0)
        form_layout.addRow("Time Step", self.time_step_spin)

        self.max_frequency_spin = _build_spin_box(1_000.0, 20_000.0, suffix=" Hz", decimals=0)
        self.max_frequency_spin.setValue(settings.max_frequency_hz)
        form_layout.addRow("Max Frequency", self.max_frequency_spin)

        self.dynamic_range_spin = _build_spin_box(20.0, 120.0, suffix=" dB", decimals=0)
        self.dynamic_range_spin.setValue(settings.dynamic_range_db)
        form_layout.addRow("Dynamic Range", self.dynamic_range_spin)

        self.preemphasis_spin = _build_spin_box(0.0, 1_000.0, suffix=" Hz", decimals=0)
        self.preemphasis_spin.setValue(settings.preemphasis_from_hz)
        form_layout.addRow("Pre-emphasis From", self.preemphasis_spin)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.reset_button = QPushButton("Praat Defaults", self)
        self.button_box.addButton(self.reset_button, QDialogButtonBox.ButtonRole.ResetRole)
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.reset_button.clicked.connect(self._reset_to_defaults)

    def settings(self) -> SpectrogramSettings:
        """Return the current dialog values as analysis settings."""
        return SpectrogramSettings(
            window_length_s=self.window_length_spin.value() / 1_000.0,
            time_step_s=self.time_step_spin.value() / 1_000.0,
            max_frequency_hz=self.max_frequency_spin.value(),
            dynamic_range_db=self.dynamic_range_spin.value(),
            preemphasis_from_hz=self.preemphasis_spin.value(),
        )

    def _reset_to_defaults(self) -> None:
        self.window_length_spin.setValue(PRAAT_DEFAULT_WINDOW_LENGTH_S * 1_000.0)
        self.time_step_spin.setValue(PRAAT_DEFAULT_TIME_STEP_S * 1_000.0)
        self.max_frequency_spin.setValue(PRAAT_DEFAULT_MAX_FREQUENCY_HZ)
        self.dynamic_range_spin.setValue(PRAAT_DEFAULT_DYNAMIC_RANGE_DB)
        self.preemphasis_spin.setValue(PRAAT_DEFAULT_PREEMPHASIS_FROM_HZ)


def _build_spin_box(minimum: float, maximum: float, *, suffix: str, decimals: int) -> QDoubleSpinBox:
    spin_box = QDoubleSpinBox()
    spin_box.setRange(minimum, maximum)
    spin_box.setDecimals(decimals)
    spin_box.setSuffix(suffix)
    spin_box.setSingleStep(0.5 if decimals > 0 else 100.0)
    return spin_box
