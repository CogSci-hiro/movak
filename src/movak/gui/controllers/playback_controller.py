from __future__ import annotations


class PlaybackController:
    """
    Controls audio playback.
    """

    def __init__(self, audio_engine) -> None:
        self.audio_engine = audio_engine

        self.playback_speed = 1.0
        self.loop_interval = None

    def play(self) -> None:
        self.audio_engine.play()

    def pause(self) -> None:
        self.audio_engine.pause()

    def toggle_play(self) -> None:
        if self.audio_engine.is_playing():
            self.pause()
        else:
            self.play()

    def set_speed(self, speed: float) -> None:
        self.playback_speed = speed
        self.audio_engine.set_speed(speed)

    def loop(self, start: float, end: float) -> None:
        self.loop_interval = (start, end)
