from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...features.analysis_inspector import FormantPoint, PowerSpectralDensityEstimate
from ..style.palette import Palette
from ..style.spacing import Spacing

REFERENCE_RANGE_MARGIN_RATIO = 0.2
PSD_PLACEHOLDER_FREQUENCY_HZ = 5_000.0
PSD_FORMANT_LINE_COLOR = (255, 165, 0)
PSD_FORMANT_LINE_WIDTH = 1.4
PSD_FORMANT_LINE_ALPHA = 210
FORMANT_DOT_FILL_ALPHA = 210
FORMANT_DOT_OUTLINE_ALPHA = 210
REFERENCE_OUTLINE_WIDTH = 1.0
REFERENCE_OUTLINE_ALPHA = 70
REFERENCE_LABEL_ALPHA = 150
REFERENCE_LABEL_Y_OFFSET_HZ = 28.0
REFERENCE_LABEL_FONT_POINT_SIZE_DELTA = 2
FORMANT_MIN_ALPHA = 24
FORMANT_MAX_ALPHA = 210
FORMANT_ALPHA_GAMMA = 1.8
FORMANT_CHANNEL_COLORS = (
    (Palette.WAVEFORM, Palette.WAVEFORM),
    (Palette.ACCENT_VIOLET, Palette.ACCENT_VIOLET),
)


@dataclass(frozen=True, slots=True)
class ReferenceVowelGuide:
    """Approximate IPA vowel landmark used as a visual guide."""

    symbol: str
    f1_hz: float
    f2_hz: float


IPA_REFERENCE_VOWELS: tuple[ReferenceVowelGuide, ...] = (
    ReferenceVowelGuide("i", 270.0, 2_290.0),
    ReferenceVowelGuide("y", 310.0, 1_870.0),
    ReferenceVowelGuide("e", 390.0, 2_000.0),
    ReferenceVowelGuide("o", 460.0, 850.0),
    ReferenceVowelGuide("ø", 430.0, 1_530.0),
    ReferenceVowelGuide("ɛ", 530.0, 1_840.0),
    ReferenceVowelGuide("ɔ", 570.0, 840.0),
    ReferenceVowelGuide("a", 730.0, 1_620.0),
    ReferenceVowelGuide("ɑ", 730.0, 1_090.0),
    ReferenceVowelGuide("u", 300.0, 870.0),
)

VOWEL_SPACE_OUTLINE_SYMBOLS: tuple[str, ...] = ("i", "e", "ɛ", "a", "ɑ", "ɔ", "o", "u", "i")


def _scaled_reference_axis_range(values_hz: tuple[float, ...]) -> tuple[float, float]:
    minimum = min(values_hz)
    maximum = max(values_hz)
    margin = (maximum - minimum) * REFERENCE_RANGE_MARGIN_RATIO
    return (minimum - margin, maximum + margin)


FORMANT_F1_AXIS_RANGE = _scaled_reference_axis_range(tuple(guide.f1_hz for guide in IPA_REFERENCE_VOWELS))
FORMANT_F2_AXIS_RANGE = _scaled_reference_axis_range(tuple(guide.f2_hz for guide in IPA_REFERENCE_VOWELS))


class AnalysisSectionWidget(QWidget):
    """Shared shell for a labeled right-panel analysis plot."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("sectionLabel")
        layout.addWidget(self.title_label)

        self.plot_widget = pg.PlotWidget(self)
        self.plot_widget.setBackground(Palette.PANEL)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.16)
        self.plot_widget.hideButtons()
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.getPlotItem().setClipToView(True)
        self.plot_widget.getPlotItem().getAxis("bottom").setPen(pg.mkPen(Palette.TEXT_DIM))
        self.plot_widget.getPlotItem().getAxis("left").setPen(pg.mkPen(Palette.TEXT_DIM))
        self.plot_widget.getPlotItem().getAxis("bottom").setTextPen(pg.mkPen(Palette.TEXT_MUTED))
        self.plot_widget.getPlotItem().getAxis("left").setTextPen(pg.mkPen(Palette.TEXT_MUTED))
        layout.addWidget(self.plot_widget, 1)

        self.state_label = QLabel(self)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.state_label.setObjectName("emptyStateText")
        self.state_label.setWordWrap(True)
        layout.addWidget(self.state_label)

    def set_state_message(self, message: str | None) -> None:
        """Show or hide the section-level placeholder text."""

        visible = bool(message)
        self.state_label.setText(message or "")
        self.state_label.setVisible(visible)


class PsdPlotWidget(AnalysisSectionWidget):
    """PSD plot specialized for the right-panel inspector."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("PSD", parent)
        self.curve_item = self.plot_widget.plot(
            pen=pg.mkPen(Palette.ACCENT, width=1.8),
        )
        self.formant_line_items: list[pg.InfiniteLine] = []
        self.plot_widget.setLabel("bottom", "Frequency", units="Hz")
        self.plot_widget.setLabel("left", "Power", units="dB")
        self.clear_plot()

    def set_psd(
        self,
        estimate: PowerSpectralDensityEstimate | None,
        formant_frequencies_hz: np.ndarray | None = None,
    ) -> None:
        """Render PSD data or keep the panel empty."""

        if estimate is None or estimate.frequencies_hz.size == 0 or estimate.power_db.size == 0:
            self.clear_plot()
            self.set_state_message("PSD unavailable for the current analysis slice.")
            return

        self.curve_item.setData(estimate.frequencies_hz, estimate.power_db)
        self._set_formant_lines(formant_frequencies_hz, max_frequency_hz=float(estimate.frequencies_hz[-1]))
        self.plot_widget.setXRange(0.0, float(estimate.frequencies_hz[-1]), padding=0.02)
        self.plot_widget.enableAutoRange(axis="y", enable=True)
        self.set_state_message(None)

    def clear_plot(self) -> None:
        """Reset the PSD plot to an empty state."""

        self.curve_item.clear()
        self._clear_formant_lines()
        self.plot_widget.setXRange(0.0, PSD_PLACEHOLDER_FREQUENCY_HZ, padding=0.0)
        self.plot_widget.setYRange(-120.0, 0.0, padding=0.0)

    def _set_formant_lines(self, formant_frequencies_hz: np.ndarray | None, *, max_frequency_hz: float) -> None:
        self._clear_formant_lines()
        if formant_frequencies_hz is None:
            return

        frequencies = np.asarray(formant_frequencies_hz, dtype=np.float32).reshape(-1)
        valid_frequencies = frequencies[
            np.isfinite(frequencies) & (frequencies > 0.0) & (frequencies <= max_frequency_hz)
        ]
        for frequency_hz in valid_frequencies:
            line_item = pg.InfiniteLine(
                pos=float(frequency_hz),
                angle=90,
                movable=False,
                pen=pg.mkPen(_color_with_alpha(PSD_FORMANT_LINE_COLOR, PSD_FORMANT_LINE_ALPHA), width=PSD_FORMANT_LINE_WIDTH),
            )
            line_item.setZValue(30)
            self.formant_line_items.append(line_item)
            self.plot_widget.addItem(line_item)

    def _clear_formant_lines(self) -> None:
        for line_item in self.formant_line_items:
            self.plot_widget.removeItem(line_item)
        self.formant_line_items.clear()


class FormantSpacePlotWidget(AnalysisSectionWidget):
    """Formant-space plot specialized for the right-panel inspector."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Formant Space", parent)
        self.reference_outline_item = pg.PlotCurveItem(
            pen=pg.mkPen(
                _color_with_alpha(Palette.TEXT_DIM, REFERENCE_OUTLINE_ALPHA),
                width=REFERENCE_OUTLINE_WIDTH,
                style=Qt.PenStyle.DashLine,
            )
        )
        self.scatter_items = [
            pg.ScatterPlotItem(
                size=11,
                brush=pg.mkBrush(_color_with_alpha(fill_color, FORMANT_DOT_FILL_ALPHA)),
                pen=pg.mkPen(_color_with_alpha(outline_color, FORMANT_DOT_OUTLINE_ALPHA), width=1.2),
            )
            for fill_color, outline_color in FORMANT_CHANNEL_COLORS
        ]
        self.reference_label_items: list[pg.TextItem] = []
        self.plot_widget.addItem(self.reference_outline_item)
        for scatter_item in self.scatter_items:
            self.plot_widget.addItem(scatter_item)
        self.plot_widget.setLabel("bottom", "F2", units="Hz")
        self.plot_widget.setLabel("left", "F1", units="Hz")
        self.plot_widget.getViewBox().invertX(True)
        self.plot_widget.getViewBox().invertY(True)
        self._build_reference_guides()
        self.reference_outline_item.setZValue(10)
        for scatter_item in self.scatter_items:
            scatter_item.setZValue(40)
        self.clear_plot()

    def set_formant_point(self, formant_point: FormantPoint | None, confidence: float | None = None) -> None:
        self.set_formant_points((formant_point,), (confidence,))

    def set_formant_points(
        self,
        formant_points: tuple[FormantPoint | None, ...] | list[FormantPoint | None],
        confidences: tuple[float | None, ...] | list[float | None] | None = None,
    ) -> None:
        """Render a representative F1/F2 point or keep the plot empty."""

        normalized_points = tuple(formant_points)
        if not any(point is not None for point in normalized_points):
            self.clear_plot()
            self.set_state_message("No reliable F1/F2 estimate for the current analysis slice.")
            return

        normalized_confidences = tuple(confidences) if confidences is not None else tuple(None for _ in normalized_points)
        for scatter_index, scatter_item in enumerate(self.scatter_items):
            if scatter_index >= len(normalized_points) or normalized_points[scatter_index] is None:
                scatter_item.setData([], [])
                continue
            formant_point = normalized_points[scatter_index]
            alpha = _alpha_from_confidence(
                normalized_confidences[scatter_index] if scatter_index < len(normalized_confidences) else None
            )
            fill_color, outline_color = FORMANT_CHANNEL_COLORS[scatter_index % len(FORMANT_CHANNEL_COLORS)]
            scatter_item.setBrush(pg.mkBrush(_color_with_alpha(fill_color, alpha)))
            scatter_item.setPen(pg.mkPen(_color_with_alpha(outline_color, alpha), width=1.2))
            scatter_item.setData([formant_point.f2_hz], [formant_point.f1_hz])
        self.plot_widget.setXRange(*FORMANT_F2_AXIS_RANGE, padding=0.0)
        self.plot_widget.setYRange(*FORMANT_F1_AXIS_RANGE, padding=0.0)
        self.set_state_message(None)

    def clear_plot(self) -> None:
        """Reset the formant-space plot to an empty state."""

        for scatter_item in self.scatter_items:
            scatter_item.setData([], [])
        self.plot_widget.setXRange(*FORMANT_F2_AXIS_RANGE, padding=0.0)
        self.plot_widget.setYRange(*FORMANT_F1_AXIS_RANGE, padding=0.0)

    def _build_reference_guides(self) -> None:
        reference_positions = {guide.symbol: guide for guide in IPA_REFERENCE_VOWELS}
        outline_points = [reference_positions[symbol] for symbol in VOWEL_SPACE_OUTLINE_SYMBOLS if symbol in reference_positions]
        self.reference_outline_item.setData(
            [point.f2_hz for point in outline_points],
            [point.f1_hz for point in outline_points],
        )
        for guide in IPA_REFERENCE_VOWELS:
            label_item = pg.TextItem(
                text=guide.symbol,
                color=_color_with_alpha(Palette.TEXT_MUTED, REFERENCE_LABEL_ALPHA),
                anchor=(0.5, 1.0),
            )
            label_font = QFont()
            label_font.setPointSize(label_font.pointSize() + REFERENCE_LABEL_FONT_POINT_SIZE_DELTA)
            label_item.setFont(label_font)
            label_item.setPos(guide.f2_hz, guide.f1_hz + REFERENCE_LABEL_Y_OFFSET_HZ)
            label_item.setZValue(30)
            self.reference_label_items.append(label_item)
            self.plot_widget.addItem(label_item)


def _color_with_alpha(color, alpha: int):
    if isinstance(color, tuple):
        return (*color[:3], alpha)
    if hasattr(color, "red") and hasattr(color, "green") and hasattr(color, "blue"):
        return (color.red(), color.green(), color.blue(), alpha)
    qt_color = QColor(color)
    return (qt_color.red(), qt_color.green(), qt_color.blue(), alpha)


def _alpha_from_confidence(confidence: float | None) -> int:
    if confidence is None:
        return FORMANT_MAX_ALPHA
    clamped_confidence = min(max(float(confidence), 0.0), 1.0)
    normalized_confidence = clamped_confidence**FORMANT_ALPHA_GAMMA
    alpha = FORMANT_MIN_ALPHA + ((FORMANT_MAX_ALPHA - FORMANT_MIN_ALPHA) * normalized_confidence)
    return int(round(min(max(alpha, FORMANT_MIN_ALPHA), FORMANT_MAX_ALPHA)))
