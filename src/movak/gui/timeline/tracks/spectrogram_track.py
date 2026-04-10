from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal

from ..timeline_track import TRACK_LEFT_AXIS_WIDTH, TimelineTrack

SPECTROGRAM_DEFAULT_HEIGHT = 132
SPECTROGRAM_TIME_BINS = 480
SPECTROGRAM_FREQUENCY_BINS = 96
PLACEHOLDER_DURATION = 12.0
PLACEHOLDER_MAX_FREQUENCY_HZ = 5_000.0
DISPLAY_TIME_UPSAMPLE = 2
DISPLAY_FREQUENCY_UPSAMPLE = 2


class SpectrogramTrack(TimelineTrack):
    """Spectrogram row displayed as an image aligned to the shared timeline.

    Parameters
    ----------
    spectrogram
        Spectrogram matrix with shape ``(frequency_bins, time_bins)``.
    duration
        Total represented duration in seconds.
    parent
        Optional parent widget.
    """

    settings_requested = pyqtSignal()

    def __init__(
        self,
        spectrogram: np.ndarray | None = None,
        duration: float = PLACEHOLDER_DURATION,
        max_frequency_hz: float = PLACEHOLDER_MAX_FREQUENCY_HZ,
        frame_step_seconds: float = 0.002,
        parent=None,
    ) -> None:
        super().__init__("spectrogram", parent)
        self.duration = duration
        self.max_frequency_hz = max(max_frequency_hz, 1.0)
        self.frame_step_seconds = max(frame_step_seconds, 1e-6)
        self.frame_start_seconds = 0.0
        self.frame_end_seconds = duration
        self.spectrogram = _normalize_spectrogram(spectrogram)
        self.display_image = _upsample_image(self.spectrogram)
        self.image_item = pg.ImageItem(axisOrder="row-major")
        self.plot_widget.addItem(self.image_item)
        self.plot_widget.setYRange(0.0, self.max_frequency_hz, padding=0.0)
        self.plot_widget.getViewBox().invertY(False)
        self.plot_widget.showAxis("left")
        self.plot_widget.getAxis("left").setWidth(TRACK_LEFT_AXIS_WIDTH)
        self.plot_widget.getAxis("left").setStyle(showValues=False, tickLength=0)
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen((0, 0, 0, 0)))
        self.plot_widget.getAxis("left").setTickPen(pg.mkPen((0, 0, 0, 0)))
        self.setMinimumHeight(SPECTROGRAM_DEFAULT_HEIGHT)
        self.image_item.setLookupTable(_build_lookup_table())
        self.image_item.setImage(self.display_image, autoLevels=False, levels=(0.0, 1.0))
        self._update_image_rect()

    def render(self, start_time: float, end_time: float) -> None:
        """Render the visible spectrogram segment."""

        self.plot_widget.setXRange(start_time, end_time, padding=0.0)

    def set_spectrogram_data(
        self,
        spectrogram: np.ndarray,
        duration: float,
        max_frequency_hz: float | None = None,
        frame_step_seconds: float | None = None,
        frame_start_seconds: float | None = None,
        frame_end_seconds: float | None = None,
    ) -> None:
        """Set spectrogram data and redraw."""
        self.spectrogram = _normalize_spectrogram(spectrogram)
        self.display_image = _upsample_image(self.spectrogram)
        self.duration = max(duration, 0.0)
        if max_frequency_hz is not None:
            self.max_frequency_hz = max(max_frequency_hz, 1.0)
        if frame_step_seconds is not None:
            self.frame_step_seconds = max(frame_step_seconds, 1e-6)
        if frame_start_seconds is not None:
            self.frame_start_seconds = frame_start_seconds
        if frame_end_seconds is not None:
            self.frame_end_seconds = max(frame_end_seconds, self.frame_start_seconds + self.frame_step_seconds)
        self.plot_widget.setYRange(0.0, self.max_frequency_hz, padding=0.0)
        self.image_item.setImage(self.display_image, autoLevels=False, levels=(0.0, 1.0))
        self._update_image_rect()
        self.render(self.visible_start_time, self.visible_end_time)

    def clear_spectrogram(self) -> None:
        """Reset to placeholder spectrogram."""
        self.spectrogram = _build_placeholder_spectrogram()
        self.display_image = _upsample_image(self.spectrogram)
        self.duration = PLACEHOLDER_DURATION
        self.max_frequency_hz = PLACEHOLDER_MAX_FREQUENCY_HZ
        self.frame_step_seconds = 0.002
        self.frame_start_seconds = 0.0
        self.frame_end_seconds = PLACEHOLDER_DURATION
        self.plot_widget.setYRange(0.0, self.max_frequency_hz, padding=0.0)
        self.image_item.setImage(self.display_image, autoLevels=False, levels=(0.0, 1.0))
        self._update_image_rect()
        self.render(self.visible_start_time, self.visible_end_time)

    def _update_image_rect(self) -> None:
        """Align the spectrogram image to timeline time coordinates."""

        image_width_seconds = max(self.frame_step_seconds, self.frame_end_seconds - self.frame_start_seconds)
        image_rect = pg.QtCore.QRectF(self.frame_start_seconds, 0.0, image_width_seconds, self.max_frequency_hz)
        self.image_item.setRect(image_rect)

    def _handle_scene_click(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.view_box.sceneBoundingRect().contains(event.scenePos()):
                self.settings_requested.emit()
                event.accept()
                return
        super()._handle_scene_click(event)

def _normalize_spectrogram(spectrogram: np.ndarray | None) -> np.ndarray:
    """Return a spectrogram image, generating a placeholder when absent."""

    if spectrogram is None:
        return _build_placeholder_spectrogram()

    image = np.asarray(spectrogram, dtype=np.float64)
    if image.ndim != 2:
        raise ValueError("SpectrogramTrack expects a 2D spectrogram array.")
    if image.size == 0:
        return _build_placeholder_spectrogram()
    return image


def _build_placeholder_spectrogram() -> np.ndarray:
    """Generate a synthetic spectrogram for the initial GUI shell."""

    time_values = np.linspace(0.0, 1.0, SPECTROGRAM_TIME_BINS, dtype=np.float64)
    frequency_values = np.linspace(0.0, 1.0, SPECTROGRAM_FREQUENCY_BINS, dtype=np.float64)
    time_grid, frequency_grid = np.meshgrid(time_values, frequency_values)
    return (
        0.35 * np.sin(time_grid * 18.0)
        + 0.25 * np.cos(frequency_grid * 24.0)
        + 0.30 * np.exp(-((frequency_grid - 0.55) ** 2) * 14.0)
        + time_grid * 0.25
    )


def _build_lookup_table() -> np.ndarray:
    """Create a dark-editor-friendly spectrogram palette."""

    colors = np.array(
        [
            (0, 0, 0, 255),
            (12, 24, 58, 255),
            (21, 76, 122, 255),
            (38, 140, 182, 255),
            (80, 210, 230, 255),
            (185, 242, 163, 255),
            (248, 226, 113, 255),
            (255, 255, 255, 255),
        ],
        dtype=np.ubyte,
    )
    return colors


def _upsample_image(image: np.ndarray) -> np.ndarray:
    """Smooth the displayed spectrogram without changing its time/frequency extent."""
    normalized = np.asarray(image, dtype=np.float32)
    if normalized.ndim != 2 or normalized.size == 0:
        return normalized

    time_upsampled = _interpolate_axis(normalized, axis=1, factor=DISPLAY_TIME_UPSAMPLE)
    return _interpolate_axis(time_upsampled, axis=0, factor=DISPLAY_FREQUENCY_UPSAMPLE)


def _interpolate_axis(image: np.ndarray, *, axis: int, factor: int) -> np.ndarray:
    if factor <= 1 or image.shape[axis] <= 1:
        return image

    original_positions = np.arange(image.shape[axis], dtype=np.float32)
    upsampled_positions = np.linspace(
        0.0,
        float(image.shape[axis] - 1),
        num=image.shape[axis] * factor,
        dtype=np.float32,
    )

    if axis == 1:
        upsampled = np.vstack([
            np.interp(upsampled_positions, original_positions, row).astype(np.float32)
            for row in image
        ])
        return upsampled

    upsampled = np.vstack([
        np.interp(upsampled_positions, original_positions, column).astype(np.float32)
        for column in image.T
    ]).T
    return upsampled
