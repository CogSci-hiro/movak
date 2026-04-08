from __future__ import annotations


class NavigationController:
    """
    Controls navigation across recording.
    """

    def __init__(self, timeline_controller) -> None:
        self.timeline_controller = timeline_controller

    def jump_to_token(self, token_id: str) -> None:
        interval = self.timeline_controller.model.get_interval(token_id)

        time = interval.start

        self.timeline_controller.jump_to_time(time)
