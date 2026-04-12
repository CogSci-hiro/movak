import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

pytest.importorskip("pyqtgraph")

from movak.annotations.model import AnnotationDocument, AnnotationTier, IntervalAnnotation
from movak.gui.controllers.annotation_editor_controller import AnnotationEditorController
from movak.gui.timeline.timeline_viewport import TimelineViewport
from movak.gui.timeline.time_axis import TimeAxis
from movak.gui.timeline.tracks.spectrogram_track import SpectrogramTrack
from movak.gui.timeline.tracks.tier_track import TIER_ROW_HEIGHT, IntervalAnnotationItem, TierTrack
from movak.gui.timeline.tracks.waveform_track import WaveformTrack


def test_timeline_viewport_clamps_visible_range_to_audio_duration():
    app = QApplication.instance() or QApplication([])
    viewport = TimelineViewport(total_duration=10.0)
    viewport.show()
    app.processEvents()

    viewport.set_visible_time_range(-5.0, 30.0)

    assert viewport.visible_start_time == 0.0
    assert viewport.visible_end_time == 10.0

    viewport.set_visible_time_range(9.9, 9.91)

    assert viewport.visible_start_time >= 0.0
    assert viewport.visible_end_time <= 10.0
    assert viewport.visible_end_time > viewport.visible_start_time

    viewport.close()


def test_timeline_viewport_can_center_on_time_within_bounds():
    app = QApplication.instance() or QApplication([])
    viewport = TimelineViewport(total_duration=12.0)
    viewport.show()
    app.processEvents()

    viewport.set_visible_time_range(2.0, 6.0)
    viewport.center_on_time(11.5)

    assert viewport.visible_end_time == 12.0
    assert viewport.visible_start_time < viewport.visible_end_time

    viewport.close()


def test_timeline_viewport_enables_scrollbar_only_when_zoomed():
    app = QApplication.instance() or QApplication([])
    viewport = TimelineViewport(total_duration=12.0)
    viewport.show()
    app.processEvents()

    viewport.fit_to_audio()
    app.processEvents()
    assert viewport.horizontal_scrollbar.isVisible() is True
    assert viewport.horizontal_scrollbar.isEnabled() is False

    viewport.set_visible_time_range(2.0, 6.0)
    app.processEvents()
    assert viewport.horizontal_scrollbar.isVisible() is True
    assert viewport.horizontal_scrollbar.isEnabled() is True

    viewport.close()


def test_timeline_viewport_emits_cursor_changes_once_per_distinct_time():
    app = QApplication.instance() or QApplication([])
    viewport = TimelineViewport(total_duration=12.0)
    viewport.show()
    app.processEvents()

    cursor_times: list[float] = []
    viewport.cursor_time_changed.connect(cursor_times.append)

    viewport.set_cursor_time(1.25)
    viewport.set_cursor_time(1.25)
    viewport.set_cursor_time(2.5)
    app.processEvents()

    assert cursor_times == [1.25, 2.5]

    viewport.close()


def test_timeline_viewport_pans_left_when_cursor_moves_before_visible_window():
    app = QApplication.instance() or QApplication([])
    viewport = TimelineViewport(total_duration=12.0)
    viewport.show()
    app.processEvents()

    viewport.set_visible_time_range(4.0, 8.0)
    viewport.set_cursor_time(2.0)
    app.processEvents()

    assert viewport.cursor_time == 2.0
    assert viewport.visible_start_time == 2.0
    assert viewport.visible_end_time == 6.0

    viewport.close()


def test_timeline_viewport_pans_right_when_cursor_moves_after_visible_window():
    app = QApplication.instance() or QApplication([])
    viewport = TimelineViewport(total_duration=12.0)
    viewport.show()
    app.processEvents()

    viewport.set_visible_time_range(2.0, 6.0)
    viewport.set_cursor_time(9.0)
    app.processEvents()

    assert viewport.cursor_time == 9.0
    assert viewport.visible_start_time == 5.0
    assert viewport.visible_end_time == 9.0

    viewport.close()


def test_waveform_and_spectrogram_tracks_reserve_matching_plot_margins():
    app = QApplication.instance() or QApplication([])
    waveform_track = WaveformTrack()
    spectrogram_track = SpectrogramTrack()
    waveform_track.show()
    spectrogram_track.show()
    app.processEvents()

    waveform_axis_width = waveform_track.plot_widget.getAxis("left").width()
    spectrogram_axis_width = spectrogram_track.plot_widget.getAxis("left").width()

    assert waveform_axis_width == spectrogram_axis_width
    assert (
        waveform_track.plot_widget.getViewBox().sceneBoundingRect().left()
        == spectrogram_track.plot_widget.getViewBox().sceneBoundingRect().left()
    )

    waveform_track.close()
    spectrogram_track.close()


def test_tier_track_renders_bracket_items_with_full_height_hit_regions():
    app = QApplication.instance() or QApplication([])
    document = AnnotationDocument(
        duration_seconds=3.0,
        tiers=[
            AnnotationTier(
                name="Words",
                tier_type="interval",
                annotations=[IntervalAnnotation(0.25, 1.75, "annotation label")],
            )
        ],
    )
    controller = AnnotationEditorController(document)
    tier_track = TierTrack(
        tier=document.tiers[0],
        controller=controller,
    )
    tier_track.show()
    tier_track.set_time_range(0.0, 3.0)
    app.processEvents()

    interval_item = next(item for item in tier_track._items if isinstance(item, IntervalAnnotationItem))
    assert interval_item.boundingRect().height() == pytest.approx(TIER_ROW_HEIGHT)
    assert interval_item.shape().boundingRect() == interval_item.boundingRect()

    tier_track.close()


def test_tier_track_direct_typing_updates_selected_annotation_label(qtbot):
    document = AnnotationDocument(
        duration_seconds=3.0,
        tiers=[
            AnnotationTier(
                name="Words",
                tier_type="interval",
                annotations=[IntervalAnnotation(0.25, 1.75, "a")],
            )
        ],
    )
    controller = AnnotationEditorController(document)
    tier_track = TierTrack(
        tier=document.tiers[0],
        controller=controller,
    )
    qtbot.addWidget(tier_track)
    tier_track.show()
    tier_track.set_time_range(0.0, 3.0)
    controller.select_annotation(document.tiers[0].id, document.tiers[0].annotations[0].id)
    tier_track.setFocus(Qt.FocusReason.OtherFocusReason)

    QTest.keyClicks(tier_track, "bc")
    QTest.keyClick(tier_track, Qt.Key.Key_Backspace)

    assert document.tiers[0].annotations[0].text == "ab"


def test_tier_track_delete_still_removes_selected_annotation(qtbot):
    document = AnnotationDocument(
        duration_seconds=3.0,
        tiers=[
            AnnotationTier(
                name="Words",
                tier_type="interval",
                annotations=[IntervalAnnotation(0.25, 1.75, "label")],
            )
        ],
    )
    controller = AnnotationEditorController(document)
    tier_track = TierTrack(
        tier=document.tiers[0],
        controller=controller,
    )
    qtbot.addWidget(tier_track)
    tier_track.show()
    tier_track.set_time_range(0.0, 3.0)
    controller.select_annotation(document.tiers[0].id, document.tiers[0].annotations[0].id)
    tier_track.setFocus(Qt.FocusReason.OtherFocusReason)

    QTest.keyClick(tier_track, Qt.Key.Key_Delete)

    assert document.tiers[0].annotations == []


def test_spectrogram_track_selection_updates_overlay_state():
    app = QApplication.instance() or QApplication([])
    spectrogram_track = SpectrogramTrack()
    spectrogram_track.show()
    app.processEvents()

    selected_points: list[tuple[float, float]] = []
    selected_regions: list[tuple[float, float, float, float]] = []
    spectrogram_track.point_selected.connect(lambda time_s, frequency_hz: selected_points.append((time_s, frequency_hz)))
    spectrogram_track.region_selected.connect(lambda start, end, low, high: selected_regions.append((start, end, low, high)))

    spectrogram_track.select_point(1.25, 1_200.0)
    app.processEvents()

    assert spectrogram_track.selected_time_seconds == 1.25
    assert spectrogram_track.selected_frequency_hz == 1_200.0
    assert spectrogram_track.point_time_line.isVisible() is True
    assert spectrogram_track.point_frequency_line.isVisible() is True
    assert selected_points[-1] == (1.25, 1_200.0)

    spectrogram_track.select_region(0.5, 1.5, 300.0, 1_800.0)
    app.processEvents()

    assert spectrogram_track.selected_region == (0.5, 1.5, 300.0, 1_800.0)
    assert spectrogram_track.selection_region_outline.isVisible() is True
    assert spectrogram_track.point_time_line.isVisible() is False
    assert spectrogram_track.point_frequency_line.isVisible() is False
    assert selected_regions[-1] == (0.5, 1.5, 300.0, 1_800.0)

    spectrogram_track.close()


def test_spectrogram_track_can_overlay_formant_points():
    app = QApplication.instance() or QApplication([])
    spectrogram_track = SpectrogramTrack()
    spectrogram_track.show()
    app.processEvents()

    spectrogram_track.set_formant_data(
        times_seconds=[0.1, 0.2, 0.3],
        frequencies_hz=[
            [500.0, 520.0, 540.0],
            [1_500.0, 1_520.0, 1_540.0],
        ],
    )
    app.processEvents()

    assert len(spectrogram_track.formant_items) >= 2
    assert spectrogram_track.formant_items[0].isVisible() is True
    assert spectrogram_track.formant_items[1].isVisible() is True

    spectrogram_track.clear_formants()
    app.processEvents()

    assert spectrogram_track.formant_items[0].isVisible() is False
    assert spectrogram_track.formant_items[1].isVisible() is False

    spectrogram_track.close()


def test_spectrogram_track_skips_very_low_confidence_formants():
    app = QApplication.instance() or QApplication([])
    spectrogram_track = SpectrogramTrack()
    spectrogram_track.show()
    app.processEvents()

    spectrogram_track.set_formant_data(
        times_seconds=[0.1, 0.2, 0.3],
        frequencies_hz=[[500.0, 520.0, 540.0]],
        frame_confidence=[0.9, 0.1, 0.6],
    )
    app.processEvents()

    points = spectrogram_track.formant_items[0].points()
    assert len(points) == 2

    spectrogram_track.close()


def test_time_axis_can_show_precise_selected_time_marker():
    app = QApplication.instance() or QApplication([])
    axis = TimeAxis()
    axis.show()
    app.processEvents()

    axis.set_time_range(0.0, 4.0)
    axis.set_selected_time(1.234)

    ticks = axis.plot_widget.getAxis("bottom")._tickLevels[0]
    assert any(label == "[1.234s]" for _value, label in ticks)

    axis.close()
