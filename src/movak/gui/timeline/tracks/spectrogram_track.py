from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal

from ...style.palette import Palette
from ..navigation_viewbox import TimelineViewBox
from ..timeline_track import TRACK_LEFT_AXIS_WIDTH, TimelineTrack

SPECTROGRAM_DEFAULT_HEIGHT = 132
SPECTROGRAM_TIME_BINS = 480
SPECTROGRAM_FREQUENCY_BINS = 96
PLACEHOLDER_DURATION = 12.0
PLACEHOLDER_MAX_FREQUENCY_HZ = 5_000.0
DISPLAY_TIME_UPSAMPLE = 2
DISPLAY_FREQUENCY_UPSAMPLE = 2
SPECTROGRAM_SELECTION_LINE_WIDTH = 1.25
SPECTROGRAM_SELECTION_REGION_LINE_WIDTH = 1.5
SPECTROGRAM_AXIS_TICK_TARGET_COUNT = 4
FORMANT_PEN_WIDTH = 1.0
FORMANT_SYMBOL_SIZE = 5.0
FORMANT_MIN_DRAW_CONFIDENCE = 0.15
FORMANT_MIN_ALPHA = 24
FORMANT_MAX_ALPHA = 210
FORMANT_ALPHA_GAMMA = 1.8
FORMANT_COLORS = (
    (255, 106, 106),
    (255, 136, 80),
    (255, 168, 76),
    (255, 196, 90),
    (255, 222, 120),
    (255, 240, 148),
)


class SpectrogramSelectionViewBox(TimelineViewBox):
    """ViewBox that turns spectrogram clicks and drags into selections."""

    point_selected = pyqtSignal(float, float)
    region_selected = pyqtSignal(float, float, float, float)

    def mouseClickEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().mouseClickEvent(event)
            return

        clicked_point = self.mapSceneToView(event.scenePos())
        self.point_selected.emit(float(clicked_point.x()), float(clicked_point.y()))
        event.accept()

    def mouseDragEvent(self, event, axis=None) -> None:
        if event.button() != Qt.MouseButton.LeftButton or event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().mouseDragEvent(event, axis=axis)
            return

        start_point = self.mapSceneToView(event.buttonDownScenePos())
        end_point = self.mapSceneToView(event.scenePos())
        self.region_selected.emit(
            float(start_point.x()),
            float(end_point.x()),
            float(start_point.y()),
            float(end_point.y()),
        )
        event.accept()


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
    point_selected = pyqtSignal(float, float)
    region_selected = pyqtSignal(float, float, float, float)

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
        self.formant_times_seconds = np.zeros(0, dtype=np.float32)
        self.formant_frequencies_hz = np.zeros((0, 0), dtype=np.float32)
        self.formant_frame_confidence = np.zeros(0, dtype=np.float32)
        self.selected_time_seconds: float | None = None
        self.selected_frequency_hz: float | None = None
        self.selected_region: tuple[float, float, float, float] | None = None
        self.spectrogram = _normalize_spectrogram(spectrogram)
        self.display_image = _upsample_image(self.spectrogram)
        self.image_item = pg.ImageItem(axisOrder="row-major")
        self.plot_widget.addItem(self.image_item)
        self.plot_widget.setYRange(0.0, self.max_frequency_hz, padding=0.0)
        self.plot_widget.getViewBox().invertY(False)
        self.plot_widget.showAxis("left")
        self.plot_widget.getAxis("left").setWidth(TRACK_LEFT_AXIS_WIDTH)
        self.plot_widget.getAxis("left").setStyle(showValues=True, tickLength=4)
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen(Palette.TEXT_MUTED))
        self.plot_widget.getAxis("left").setTickPen(pg.mkPen(Palette.BORDER_STRONG, width=1))
        self.plot_widget.getAxis("left").setPen(pg.mkPen(Palette.TEXT_MUTED, width=1))
        self.setMinimumHeight(SPECTROGRAM_DEFAULT_HEIGHT)
        self.image_item.setLookupTable(_build_lookup_table())
        self.image_item.setImage(self.display_image, autoLevels=False, levels=(0.0, 1.0))
        self.point_time_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(Palette.ACCENT, width=SPECTROGRAM_SELECTION_LINE_WIDTH),
        )
        self.point_frequency_line = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=pg.mkPen(Palette.ACCENT, width=SPECTROGRAM_SELECTION_LINE_WIDTH),
        )
        self.selection_region_outline = pg.PlotCurveItem(
            pen=pg.mkPen(Palette.ACCENT_VIOLET, width=SPECTROGRAM_SELECTION_REGION_LINE_WIDTH),
        )
        self.formant_items: list[pg.ScatterPlotItem] = []
        self.plot_widget.addItem(self.point_time_line)
        self.plot_widget.addItem(self.point_frequency_line)
        self.plot_widget.addItem(self.selection_region_outline)
        self.point_time_line.setVisible(False)
        self.point_frequency_line.setVisible(False)
        self.selection_region_outline.setVisible(False)
        self.view_box.point_selected.connect(self.select_point)
        self.view_box.region_selected.connect(self.select_region)
        self._update_image_rect()
        self._update_frequency_axis_ticks()

    def _create_view_box(self) -> SpectrogramSelectionViewBox:
        return SpectrogramSelectionViewBox()

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
        self._update_frequency_axis_ticks()
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
        self.clear_selection()
        self.clear_formants()
        self._update_frequency_axis_ticks()
        self.render(self.visible_start_time, self.visible_end_time)

    def set_formant_data(
        self,
        times_seconds: np.ndarray,
        frequencies_hz: np.ndarray,
        frame_confidence: np.ndarray | None = None,
    ) -> None:
        """Overlay Praat-style formant points onto the spectrogram."""

        self.formant_times_seconds = np.asarray(times_seconds, dtype=np.float32).reshape(-1)
        normalized_frequencies = np.asarray(frequencies_hz, dtype=np.float32)
        if normalized_frequencies.ndim != 2:
            raise ValueError("SpectrogramTrack expects formant frequencies shaped as (formants, frames).")
        if normalized_frequencies.shape[1] != self.formant_times_seconds.size:
            raise ValueError("Formant times and frequency tracks must have matching frame counts.")
        normalized_confidence = (
            np.asarray(frame_confidence, dtype=np.float32).reshape(-1)
            if frame_confidence is not None
            else np.ones(self.formant_times_seconds.size, dtype=np.float32)
        )
        if normalized_confidence.size != self.formant_times_seconds.size:
            raise ValueError("Formant frame confidence must match the formant frame count.")

        self.formant_frequencies_hz = normalized_frequencies
        self.formant_frame_confidence = np.clip(normalized_confidence, 0.0, 1.0)
        self._ensure_formant_items(normalized_frequencies.shape[0])
        for formant_index, item in enumerate(self.formant_items):
            if formant_index >= normalized_frequencies.shape[0]:
                item.clear()
                item.setVisible(False)
                continue

            formant_values = normalized_frequencies[formant_index]
            valid_mask = (
                np.isfinite(formant_values)
                & (formant_values > 0.0)
                & (formant_values <= self.max_frequency_hz)
                & (self.formant_frame_confidence >= FORMANT_MIN_DRAW_CONFIDENCE)
            )
            if not np.any(valid_mask):
                item.clear()
                item.setVisible(False)
                continue

            item.setData(
                [
                    {
                        "pos": (float(time_seconds), float(frequency_hz)),
                        "pen": pg.mkPen((*FORMANT_COLORS[formant_index % len(FORMANT_COLORS)], _alpha_from_confidence(float(confidence))), width=FORMANT_PEN_WIDTH),
                        "brush": pg.mkBrush(0, 0, 0, 0),
                        "size": FORMANT_SYMBOL_SIZE,
                    }
                    for time_seconds, frequency_hz, confidence in zip(
                        self.formant_times_seconds[valid_mask],
                        formant_values[valid_mask],
                        self.formant_frame_confidence[valid_mask],
                        strict=False,
                    )
                ]
            )
            item.setVisible(True)

    def clear_formants(self) -> None:
        """Remove any formant overlay from the spectrogram."""

        self.formant_times_seconds = np.zeros(0, dtype=np.float32)
        self.formant_frequencies_hz = np.zeros((0, 0), dtype=np.float32)
        self.formant_frame_confidence = np.zeros(0, dtype=np.float32)
        for item in self.formant_items:
            item.clear()
            item.setVisible(False)

    def select_point(self, time_seconds: float, frequency_hz: float) -> None:
        """Select a single spectrogram point and show crosshair overlays."""

        clamped_time = _clamp(time_seconds, self.frame_start_seconds, self.frame_end_seconds)
        clamped_frequency = _clamp(frequency_hz, 0.0, self.max_frequency_hz)
        self.selected_time_seconds = clamped_time
        self.selected_frequency_hz = clamped_frequency
        self.selected_region = None

        self.point_time_line.setValue(clamped_time)
        self.point_frequency_line.setValue(clamped_frequency)
        self.point_time_line.setVisible(True)
        self.point_frequency_line.setVisible(True)
        self.selection_region_outline.setVisible(False)
        self._update_frequency_axis_ticks()
        self.point_selected.emit(clamped_time, clamped_frequency)

    def select_region(
        self,
        start_time_seconds: float,
        end_time_seconds: float,
        start_frequency_hz: float,
        end_frequency_hz: float,
    ) -> None:
        """Select a rectangular spectrotemporal region."""

        left_time = _clamp(min(start_time_seconds, end_time_seconds), self.frame_start_seconds, self.frame_end_seconds)
        right_time = _clamp(max(start_time_seconds, end_time_seconds), self.frame_start_seconds, self.frame_end_seconds)
        low_frequency = _clamp(min(start_frequency_hz, end_frequency_hz), 0.0, self.max_frequency_hz)
        high_frequency = _clamp(max(start_frequency_hz, end_frequency_hz), 0.0, self.max_frequency_hz)

        self.selected_time_seconds = None
        self.selected_frequency_hz = None
        self.selected_region = (left_time, right_time, low_frequency, high_frequency)

        self.point_time_line.setVisible(False)
        self.point_frequency_line.setVisible(False)
        self.selection_region_outline.setData(
            [left_time, right_time, right_time, left_time, left_time],
            [low_frequency, low_frequency, high_frequency, high_frequency, low_frequency],
        )
        self.selection_region_outline.setVisible(True)
        self._update_frequency_axis_ticks()
        self.region_selected.emit(left_time, right_time, low_frequency, high_frequency)

    def clear_selection(self) -> None:
        """Clear any active point or region selection."""

        self.selected_time_seconds = None
        self.selected_frequency_hz = None
        self.selected_region = None
        self.point_time_line.setVisible(False)
        self.point_frequency_line.setVisible(False)
        self.selection_region_outline.setVisible(False)

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

    def _update_frequency_axis_ticks(self) -> None:
        axis = self.plot_widget.getAxis("left")
        tick_step = _select_frequency_tick_step(self.max_frequency_hz / SPECTROGRAM_AXIS_TICK_TARGET_COUNT)

        major_ticks: list[tuple[float, str]] = []
        tick_frequency = 0.0
        while tick_frequency <= self.max_frequency_hz + tick_step:
            if tick_frequency <= self.max_frequency_hz:
                major_ticks.append((tick_frequency, _format_frequency_label(tick_frequency)))
            tick_frequency += tick_step

        if self.selected_frequency_hz is not None:
            selected_label = f"[{self.selected_frequency_hz:.0f} Hz]"
            if not any(abs(tick_value - self.selected_frequency_hz) < 1e-6 for tick_value, _ in major_ticks):
                major_ticks.append((self.selected_frequency_hz, selected_label))
            else:
                major_ticks = [
                    (tick_value, selected_label if abs(tick_value - self.selected_frequency_hz) < 1e-6 else label)
                    for tick_value, label in major_ticks
                ]
            major_ticks.sort(key=lambda item: item[0])

        axis.setTicks([major_ticks])

    def _ensure_formant_items(self, count: int) -> None:
        while len(self.formant_items) < count:
            color = FORMANT_COLORS[len(self.formant_items) % len(FORMANT_COLORS)]
            item = pg.ScatterPlotItem(
                size=FORMANT_SYMBOL_SIZE,
                pen=pg.mkPen((*color, FORMANT_MAX_ALPHA), width=FORMANT_PEN_WIDTH),
                brush=pg.mkBrush(0, 0, 0, 0),
                symbol="o",
                pxMode=True,
            )
            item.setVisible(False)
            self.formant_items.append(item)
            self.plot_widget.addItem(item)

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


def _format_frequency_label(frequency_hz: float) -> str:
    if frequency_hz >= 1_000.0:
        return f"{frequency_hz / 1_000.0:.1f}k"
    return f"{frequency_hz:.0f}"


def _select_frequency_tick_step(target_step: float) -> float:
    tick_steps = [100.0, 200.0, 500.0, 1_000.0, 2_000.0, 5_000.0]
    for candidate in tick_steps:
        if candidate >= max(target_step, 1.0):
            return candidate
    return 10_000.0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _alpha_from_confidence(confidence: float) -> int:
    clamped_confidence = _clamp(confidence, 0.0, 1.0)
    normalized_confidence = clamped_confidence**FORMANT_ALPHA_GAMMA
    alpha = FORMANT_MIN_ALPHA + ((FORMANT_MAX_ALPHA - FORMANT_MIN_ALPHA) * normalized_confidence)
    return int(round(_clamp(alpha, FORMANT_MIN_ALPHA, FORMANT_MAX_ALPHA)))
