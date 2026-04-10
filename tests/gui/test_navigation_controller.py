from movak.gui.controllers.navigation_controller import NavigationController


class FakeTimelineViewport:
    def __init__(self) -> None:
        self.total_duration = 12.0
        self.visible_start_time = 2.0
        self.visible_end_time = 5.0
        self.fit_calls = 0
        self.center_calls: list[float] = []

    def fit_to_audio(self) -> None:
        self.fit_calls += 1

    def center_on_time(self, time_s: float) -> None:
        self.center_calls.append(time_s)


class FakePlaybackState:
    def __init__(self, position_ms: int) -> None:
        self.position_ms = position_ms


def test_navigation_controller_fits_to_audio():
    viewport = FakeTimelineViewport()
    controller = NavigationController(viewport, FakePlaybackState(position_ms=0))

    controller.fit_to_audio()

    assert viewport.fit_calls == 1


def test_navigation_controller_centers_on_playhead():
    viewport = FakeTimelineViewport()
    controller = NavigationController(viewport, FakePlaybackState(position_ms=3_250))

    controller.center_on_playhead()

    assert viewport.center_calls == [3.25]


def test_navigation_controller_ignores_center_when_duration_is_empty():
    viewport = FakeTimelineViewport()
    viewport.total_duration = 0.0
    controller = NavigationController(viewport, FakePlaybackState(position_ms=3_250))

    controller.center_on_playhead()

    assert viewport.center_calls == []
