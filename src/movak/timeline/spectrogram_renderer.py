"""Spectrogram rendering helpers built on top of cached tiles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from movak.timeline.spectrogram_tiles import SpectrogramTile, SpectrogramTileManager
from movak.timeline.viewport import TimelineViewport

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover - optional during headless tests
    pg = None


@dataclass(slots=True)
class SpectrogramRenderResult:
    """Spectrogram image data ready for drawing."""

    image: np.ndarray
    x_offset: float
    x_scale: float
    y_scale: float
    tiles: list[SpectrogramTile]


class SpectrogramRenderer:
    """Render spectrogram tiles for the visible viewport.

    Parameters
    ----------
    tile_manager
        Tile manager providing visible spectrogram tiles.
    image_item
        Optional pyqtgraph image item updated during render.
    """

    def __init__(self, tile_manager: SpectrogramTileManager, image_item=None) -> None:
        self.tile_manager = tile_manager
        self.image_item = image_item

    def render(self, viewport: TimelineViewport) -> SpectrogramRenderResult:
        """Render the visible spectrogram segment for a viewport."""

        tiles = self.tile_manager.get_tiles(
            viewport.visible_start_time,
            viewport.visible_end_time,
        )
        result = _assemble_visible_spectrogram(tiles)

        if self.image_item is not None and pg is not None:
            self.image_item.setImage(result.image, autoLevels=False)
            rect = pg.QtCore.QRectF(
                result.x_offset,
                0.0,
                result.x_scale * result.image.shape[1],
                result.y_scale * result.image.shape[0],
            )
            self.image_item.setRect(rect)
        return result


def _assemble_visible_spectrogram(tiles: list[SpectrogramTile]) -> SpectrogramRenderResult:
    """Concatenate visible tiles into one image and scale definition."""

    if not tiles:
        empty_image = np.zeros((0, 0), dtype=np.float64)
        return SpectrogramRenderResult(
            image=empty_image,
            x_offset=0.0,
            x_scale=1.0,
            y_scale=1.0,
            tiles=[],
        )

    non_empty_tiles = [tile for tile in tiles if tile.magnitude.size > 0]
    if not non_empty_tiles:
        first_tile = tiles[0]
        empty_image = np.zeros((first_tile.frequency_values.size, 0), dtype=np.float64)
        y_scale = _compute_frequency_scale(first_tile)
        return SpectrogramRenderResult(
            image=empty_image,
            x_offset=first_tile.start_time,
            x_scale=1.0,
            y_scale=y_scale,
            tiles=tiles,
        )

    image = np.concatenate([tile.magnitude for tile in non_empty_tiles], axis=1)
    first_tile = non_empty_tiles[0]
    x_scale = _compute_time_scale(first_tile)
    y_scale = _compute_frequency_scale(first_tile)

    return SpectrogramRenderResult(
        image=image,
        x_offset=first_tile.time_values[0] if first_tile.time_values.size else first_tile.start_time,
        x_scale=x_scale,
        y_scale=y_scale,
        tiles=tiles,
    )


def _compute_time_scale(tile: SpectrogramTile) -> float:
    """Compute one image-column duration in seconds."""

    if tile.time_values.size <= 1:
        return tile.end_time - tile.start_time
    return float(tile.time_values[1] - tile.time_values[0])


def _compute_frequency_scale(tile: SpectrogramTile) -> float:
    """Compute one image-row height in Hz."""

    if tile.frequency_values.size <= 1:
        return 1.0
    return float(tile.frequency_values[1] - tile.frequency_values[0])
