"""Tile cache tests."""

from __future__ import annotations

from movak.timeline.tile_cache import TileCache


def test_tile_cache_evicts_least_recently_used_items() -> None:
    """Cache eviction removes the oldest unused entry first."""

    cache = TileCache[str](max_items=2, max_bytes=1024)

    cache.put("a", "tile-a", 100)
    cache.put("b", "tile-b", 100)
    assert cache.get("a") == "tile-a"

    cache.put("c", "tile-c", 100)

    assert "a" in cache
    assert "b" not in cache
    assert "c" in cache


def test_tile_cache_respects_byte_budget() -> None:
    """Byte-budget eviction keeps memory use bounded."""

    cache = TileCache[str](max_items=10, max_bytes=150)

    cache.put("a", "tile-a", 100)
    cache.put("b", "tile-b", 100)

    assert len(cache) == 1
