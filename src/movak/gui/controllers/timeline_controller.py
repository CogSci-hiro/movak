from __future__ import annotations

from typing import Optional

from movak.core.operations import (
    split_interval,
    merge_intervals,
    move_boundary,
    relabel_interval,
)


class TimelineController:
    """
    Controller handling timeline editing interactions.

    GUI emits events → controller translates them to operations.
    """

    def __init__(self, annotation_model) -> None:
        self.model = annotation_model

        self.selected_token: Optional[str] = None

    # --------------------------------------------------
    # Selection
    # --------------------------------------------------

    def select_interval(self, token_id: str) -> None:
        self.selected_token = token_id

    # --------------------------------------------------
    # Editing
    # --------------------------------------------------

    def split_interval(self, time: float) -> None:
        if self.selected_token is None:
            return

        split_interval(
            model=self.model,
            token_id=self.selected_token,
            time=time,
        )

    def merge_with_next(self) -> None:
        if self.selected_token is None:
            return

        merge_intervals(
            model=self.model,
            token_id=self.selected_token,
        )

    def move_boundary(self, token_id: str, new_time: float) -> None:
        move_boundary(
            model=self.model,
            token_id=token_id,
            new_time=new_time,
        )

    def relabel_interval(self, token_id: str, label: str) -> None:
        relabel_interval(
            model=self.model,
            token_id=token_id,
            label=label,
        )

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def jump_to_time(self, time: float) -> None:
        """
        Called when clicking plots or global timeline.
        """

        # GUI listens to this event
        pass
