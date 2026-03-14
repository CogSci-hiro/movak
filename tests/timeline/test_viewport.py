"""Viewport tests."""

from movak.timeline.viewport import Viewport


def test_viewport_placeholder() -> None:
    """Viewport test placeholder."""
    viewport = Viewport()
    assert isinstance(viewport, Viewport)
