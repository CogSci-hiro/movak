import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

pytest.importorskip("pyqtgraph")

from movak.gui.timeline.timeline_viewport import TimelineViewport
from movak.gui.timeline.tracks.spectrogram_track import SpectrogramTrack
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
