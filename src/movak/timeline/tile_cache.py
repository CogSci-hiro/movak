"""Tile cache utilities for timeline rendering."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, Hashable, TypeVar

T = TypeVar("T")

DEFAULT_MAX_ITEMS = 128
DEFAULT_MAX_BYTES = 64 * 1024 * 1024


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    """Internal cache entry with approximate memory cost."""

    value: T
    size_bytes: int


class TileCache(Generic[T]):
    """Simple LRU cache with item and byte limits.

    Parameters
    ----------
    max_items
        Maximum number of cached entries.
    max_bytes
        Maximum approximate memory footprint.
    """

    def __init__(self, max_items: int = DEFAULT_MAX_ITEMS, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be positive.")
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive.")

        self.max_items = max_items
        self.max_bytes = max_bytes
        self._entries: OrderedDict[Hashable, _CacheEntry[T]] = OrderedDict()
        self._current_bytes = 0

    def get(self, key: Hashable) -> T | None:
        """Return a cached item and mark it as recently used."""

        entry = self._entries.pop(key, None)
        if entry is None:
            return None
        self._entries[key] = entry
        return entry.value

    def put(self, key: Hashable, value: T, size_bytes: int) -> None:
        """Insert or replace an item in the cache."""

        if size_bytes <= 0:
            raise ValueError("size_bytes must be positive.")

        existing_entry = self._entries.pop(key, None)
        if existing_entry is not None:
            self._current_bytes -= existing_entry.size_bytes

        self._entries[key] = _CacheEntry(value=value, size_bytes=size_bytes)
        self._current_bytes += size_bytes
        self._evict_if_needed()

    def clear(self) -> None:
        """Remove all cached entries."""

        self._entries.clear()
        self._current_bytes = 0

    def __contains__(self, key: Hashable) -> bool:
        """Return whether a key is currently cached."""

        return key in self._entries

    def __len__(self) -> int:
        """Return the number of cached entries."""

        return len(self._entries)

    def _evict_if_needed(self) -> None:
        """Evict least recently used items until limits are respected."""

        while self._entries and (
            len(self._entries) > self.max_items or self._current_bytes > self.max_bytes
        ):
            _, entry = self._entries.popitem(last=False)
            self._current_bytes -= entry.size_bytes
