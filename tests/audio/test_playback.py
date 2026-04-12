import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QApplication

from movak.audio.playback import AudioPlaybackService, format_milliseconds


def test_format_milliseconds_uses_minute_and_hour_boundaries():
    assert format_milliseconds(0) == "00:00"
    assert format_milliseconds(65_000) == "01:05"
    assert format_milliseconds(3_661_000) == "01:01:01"


class FakePlayer(QObject):
    PlaybackState = QMediaPlayer.PlaybackState
    Error = QMediaPlayer.Error
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    playbackStateChanged = pyqtSignal(QMediaPlayer.PlaybackState)
    errorOccurred = pyqtSignal(QMediaPlayer.Error, str)

    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__()
        self._position = 0
        self._duration = 0
        self._playback_state = QMediaPlayer.PlaybackState.StoppedState
        self.playback_rate = 1.0
        self.play_calls = 0
        self.pause_calls = 0
        self.stop_calls = 0
        self.set_position_calls: list[int] = []
        self.source = None
        self.audio_output = None

    def setAudioOutput(self, audio_output) -> None:
        self.audio_output = audio_output

    def setSource(self, source) -> None:
        self.source = source

    def setPlaybackRate(self, playback_rate: float) -> None:
        self.playback_rate = playback_rate

    def play(self) -> None:
        self.play_calls += 1
        self._playback_state = QMediaPlayer.PlaybackState.PlayingState

    def pause(self) -> None:
        self.pause_calls += 1
        self._playback_state = QMediaPlayer.PlaybackState.PausedState

    def stop(self) -> None:
        self.stop_calls += 1
        self._playback_state = QMediaPlayer.PlaybackState.StoppedState

    def setPosition(self, position_ms: int) -> None:
        self._position = position_ms
        self.set_position_calls.append(position_ms)

    def position(self) -> int:
        return self._position

    def duration(self) -> int:
        return self._duration

    def playbackState(self) -> QMediaPlayer.PlaybackState:
        return self._playback_state

    def error(self) -> QMediaPlayer.Error:
        return QMediaPlayer.Error.NoError

    def errorString(self) -> str:
        return ""


class FakeAudioOutput:
    def __init__(self, *_args, **_kwargs) -> None:
        self.volume = 0.0

    def setVolume(self, volume: float) -> None:
        self.volume = volume


def test_audio_playback_service_seeks_to_loop_start_before_play(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("movak.audio.playback.QMediaPlayer", FakePlayer)
    monkeypatch.setattr("movak.audio.playback.QAudioOutput", FakeAudioOutput)

    service = AudioPlaybackService()
    service.set_loop_range_ms(500, 1_500)
    service.set_loop_enabled(True)
    service.player._position = 2_400

    service.play()
    app.processEvents()

    assert service.player.set_position_calls == [500]
    assert service.player.play_calls == 1


def test_audio_playback_service_wraps_back_to_loop_start_while_playing(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("movak.audio.playback.QMediaPlayer", FakePlayer)
    monkeypatch.setattr("movak.audio.playback.QAudioOutput", FakeAudioOutput)

    service = AudioPlaybackService()
    positions: list[int] = []
    service.position_changed.connect(positions.append)
    service.set_loop_range_ms(500, 1_500)
    service.set_loop_enabled(True)
    service.player._playback_state = QMediaPlayer.PlaybackState.PlayingState

    service._on_position_changed(1_500)

    assert service.player.set_position_calls == [500]
    assert positions == []


def test_audio_playback_service_sets_playback_rate(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("movak.audio.playback.QMediaPlayer", FakePlayer)
    monkeypatch.setattr("movak.audio.playback.QAudioOutput", FakeAudioOutput)

    service = AudioPlaybackService()
    service.set_playback_rate(1.5)
    app.processEvents()

    assert service.player.playback_rate == 1.5
