from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...audio.spectrogram import (
    PRAAT_DEFAULT_DYNAMIC_RANGE_DB,
    PRAAT_DEFAULT_FORMANT_MAX_FREQUENCY_HZ,
    PRAAT_DEFAULT_FORMANT_PREEMPHASIS_FROM_HZ,
    PRAAT_DEFAULT_FORMANT_WINDOW_LENGTH_S,
    PRAAT_DEFAULT_MAX_FREQUENCY_HZ,
    PRAAT_DEFAULT_MAX_NUMBER_OF_FORMANTS,
    PRAAT_DEFAULT_PREEMPHASIS_FROM_HZ,
    PRAAT_DEFAULT_SHOW_FORMANTS,
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
        self.resize(380, 320)

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

        self.show_formants_checkbox = QCheckBox("Overlay Praat formants", self)
        self.show_formants_checkbox.setChecked(settings.show_formants)
        form_layout.addRow("", self.show_formants_checkbox)

        self.max_number_of_formants_spin = QSpinBox(self)
        self.max_number_of_formants_spin.setRange(1, 8)
        self.max_number_of_formants_spin.setValue(settings.max_number_of_formants)
        form_layout.addRow("Max Formants", self.max_number_of_formants_spin)

        self.formant_max_frequency_spin = _build_spin_box(1_000.0, 8_000.0, suffix=" Hz", decimals=0)
        self.formant_max_frequency_spin.setValue(settings.formant_max_frequency_hz)
        form_layout.addRow("Formant Ceiling", self.formant_max_frequency_spin)

        self.formant_window_length_spin = _build_spin_box(5.0, 100.0, suffix=" ms", decimals=1)
        self.formant_window_length_spin.setValue(settings.formant_window_length_s * 1_000.0)
        form_layout.addRow("Formant Window", self.formant_window_length_spin)

        self.formant_preemphasis_spin = _build_spin_box(0.0, 1_000.0, suffix=" Hz", decimals=0)
        self.formant_preemphasis_spin.setValue(settings.formant_preemphasis_from_hz)
        form_layout.addRow("Formant Pre-emphasis", self.formant_preemphasis_spin)

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
        self.show_formants_checkbox.toggled.connect(self._sync_formant_controls)
        self._sync_formant_controls(self.show_formants_checkbox.isChecked())

    def settings(self) -> SpectrogramSettings:
        """Return the current dialog values as analysis settings."""
        return SpectrogramSettings(
            window_length_s=self.window_length_spin.value() / 1_000.0,
            time_step_s=self.time_step_spin.value() / 1_000.0,
            max_frequency_hz=self.max_frequency_spin.value(),
            dynamic_range_db=self.dynamic_range_spin.value(),
            preemphasis_from_hz=self.preemphasis_spin.value(),
            show_formants=self.show_formants_checkbox.isChecked(),
            max_number_of_formants=self.max_number_of_formants_spin.value(),
            formant_max_frequency_hz=self.formant_max_frequency_spin.value(),
            formant_window_length_s=self.formant_window_length_spin.value() / 1_000.0,
            formant_preemphasis_from_hz=self.formant_preemphasis_spin.value(),
        )

    def _reset_to_defaults(self) -> None:
        self.window_length_spin.setValue(PRAAT_DEFAULT_WINDOW_LENGTH_S * 1_000.0)
        self.time_step_spin.setValue(PRAAT_DEFAULT_TIME_STEP_S * 1_000.0)
        self.max_frequency_spin.setValue(PRAAT_DEFAULT_MAX_FREQUENCY_HZ)
        self.dynamic_range_spin.setValue(PRAAT_DEFAULT_DYNAMIC_RANGE_DB)
        self.preemphasis_spin.setValue(PRAAT_DEFAULT_PREEMPHASIS_FROM_HZ)
        self.show_formants_checkbox.setChecked(PRAAT_DEFAULT_SHOW_FORMANTS)
        self.max_number_of_formants_spin.setValue(PRAAT_DEFAULT_MAX_NUMBER_OF_FORMANTS)
        self.formant_max_frequency_spin.setValue(PRAAT_DEFAULT_FORMANT_MAX_FREQUENCY_HZ)
        self.formant_window_length_spin.setValue(PRAAT_DEFAULT_FORMANT_WINDOW_LENGTH_S * 1_000.0)
        self.formant_preemphasis_spin.setValue(PRAAT_DEFAULT_FORMANT_PREEMPHASIS_FROM_HZ)

    def _sync_formant_controls(self, enabled: bool) -> None:
        self.max_number_of_formants_spin.setEnabled(enabled)
        self.formant_max_frequency_spin.setEnabled(enabled)
        self.formant_window_length_spin.setEnabled(enabled)
        self.formant_preemphasis_spin.setEnabled(enabled)


def _build_spin_box(minimum: float, maximum: float, *, suffix: str, decimals: int) -> QDoubleSpinBox:
    spin_box = QDoubleSpinBox()
    spin_box.setRange(minimum, maximum)
    spin_box.setDecimals(decimals)
    spin_box.setSuffix(suffix)
    spin_box.setSingleStep(0.5 if decimals > 0 else 100.0)
    return spin_box
