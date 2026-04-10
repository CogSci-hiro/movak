from movak.audio.playback import format_milliseconds


def test_format_milliseconds_uses_minute_and_hour_boundaries():
    assert format_milliseconds(0) == "00:00"
    assert format_milliseconds(65_000) == "01:05"
    assert format_milliseconds(3_661_000) == "01:01:01"
