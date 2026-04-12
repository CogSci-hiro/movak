import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

pytest.importorskip("pyqtgraph")

from movak.features.analysis_inspector import FormantPoint, PowerSpectralDensityEstimate
from movak.gui.widgets.analysis_plot_widgets import (
    IPA_REFERENCE_VOWELS,
    FORMANT_F1_AXIS_RANGE,
    FORMANT_F2_AXIS_RANGE,
    FormantSpacePlotWidget,
    PsdPlotWidget,
)


def test_formant_space_plot_widget_builds_reference_guides():
    app = QApplication.instance() or QApplication([])
    widget = FormantSpacePlotWidget()
    widget.show()
    app.processEvents()

    assert len(widget.reference_label_items) == len(IPA_REFERENCE_VOWELS)

    widget.close()


def test_formant_space_plot_widget_keeps_live_point_on_f2_f1_axes():
    app = QApplication.instance() or QApplication([])
    widget = FormantSpacePlotWidget()
    widget.show()
    app.processEvents()

    initial_view_range = widget.plot_widget.getViewBox().viewRange()
    widget.set_formant_point(FormantPoint(f1_hz=500.0, f2_hz=1_500.0))
    app.processEvents()

    points = widget.scatter_items[0].points()
    assert len(points) == 1
    point = points[0].pos()
    assert point.x() == pytest.approx(1_500.0)
    assert point.y() == pytest.approx(500.0)
    updated_view_range = widget.plot_widget.getViewBox().viewRange()
    assert updated_view_range[0][0] == pytest.approx(initial_view_range[0][0], abs=1e-3)
    assert updated_view_range[0][1] == pytest.approx(initial_view_range[0][1], abs=1e-3)
    assert updated_view_range[1][0] == pytest.approx(initial_view_range[1][0], abs=1e-3)
    assert updated_view_range[1][1] == pytest.approx(initial_view_range[1][1], abs=1e-3)

    widget.close()


def test_formant_space_plot_widget_scales_live_point_alpha_with_confidence():
    app = QApplication.instance() or QApplication([])
    widget = FormantSpacePlotWidget()
    widget.show()
    app.processEvents()

    widget.set_formant_point(FormantPoint(f1_hz=500.0, f2_hz=1_500.0), confidence=0.0)
    app.processEvents()
    low_alpha = widget.scatter_items[0].opts["brush"].color().alpha()

    widget.set_formant_point(FormantPoint(f1_hz=500.0, f2_hz=1_500.0), confidence=1.0)
    app.processEvents()
    high_alpha = widget.scatter_items[0].opts["brush"].color().alpha()

    assert low_alpha < high_alpha

    widget.close()


def test_formant_space_plot_widget_can_render_stereo_channel_points():
    app = QApplication.instance() or QApplication([])
    widget = FormantSpacePlotWidget()
    widget.show()
    app.processEvents()

    widget.set_formant_points(
        (FormantPoint(f1_hz=500.0, f2_hz=1_500.0), FormantPoint(f1_hz=650.0, f2_hz=1_200.0)),
        (0.9, 0.4),
    )
    app.processEvents()

    left_points = widget.scatter_items[0].points()
    right_points = widget.scatter_items[1].points()
    assert len(left_points) == 1
    assert len(right_points) == 1
    assert left_points[0].pos().x() == pytest.approx(1_500.0)
    assert left_points[0].pos().y() == pytest.approx(500.0)
    assert right_points[0].pos().x() == pytest.approx(1_200.0)
    assert right_points[0].pos().y() == pytest.approx(650.0)

    widget.close()


def test_formant_space_plot_widget_ignores_extreme_outlier_ranges():
    app = QApplication.instance() or QApplication([])
    widget = FormantSpacePlotWidget()
    widget.show()
    app.processEvents()

    initial_view_range = widget.plot_widget.getViewBox().viewRange()
    widget.set_formant_point(FormantPoint(f1_hz=4_000.0, f2_hz=9_000.0), confidence=0.2)
    app.processEvents()

    view_range = widget.plot_widget.getViewBox().viewRange()
    assert view_range[0][0] == pytest.approx(initial_view_range[0][0], abs=1e-3)
    assert view_range[0][1] == pytest.approx(initial_view_range[0][1], abs=1e-3)
    assert view_range[1][0] == pytest.approx(initial_view_range[1][0], abs=1e-3)
    assert view_range[1][1] == pytest.approx(initial_view_range[1][1], abs=1e-3)
    assert view_range[0][0] == pytest.approx(FORMANT_F2_AXIS_RANGE[0], abs=1e-3)
    assert view_range[0][1] == pytest.approx(FORMANT_F2_AXIS_RANGE[1], abs=1e-3)
    assert view_range[1][0] == pytest.approx(FORMANT_F1_AXIS_RANGE[0], abs=1e-3)
    assert view_range[1][1] == pytest.approx(FORMANT_F1_AXIS_RANGE[1], abs=1e-3)

    widget.close()


def test_psd_plot_widget_draws_formant_lines_at_representative_frequencies():
    app = QApplication.instance() or QApplication([])
    widget = PsdPlotWidget()
    widget.show()
    app.processEvents()

    widget.set_psd(
        PowerSpectralDensityEstimate(
            frequencies_hz=np.array([0.0, 500.0, 1_000.0, 2_000.0, 3_000.0], dtype=np.float32),
            power_db=np.array([-90.0, -50.0, -25.0, -40.0, -55.0], dtype=np.float32),
        ),
        np.array([550.0, 1_450.0, np.nan, 3_500.0], dtype=np.float32),
    )
    app.processEvents()

    assert [line.value() for line in widget.formant_line_items] == pytest.approx([550.0, 1_450.0])

    widget.close()
