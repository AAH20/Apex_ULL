"""
ULL Skip List
=============

Probabilistic ordered map with O(log n) expected operations.

Skip lists provide ordered key-value storage with simpler implementation
than balanced trees while maintaining similar average-case performance.
The probabilistic balancing avoids the complex rebalancing logic of
AVL or red-black trees.

Optimizations:
- Max level capped at 32 (supports up to 2^32 elements)
- Randomized level generation with p=0.25
- Forward-only links for cache-friendly iteration
- No rebalancing needed (probabilistic balance)

Latency: ~100-500 ns per operation (depends on height)
"""

from __future__ import annotations

import random
from typing import Generic, Iterator, List, Optional, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")

_MAX_LEVEL = 32
_P = 0.25


class _Node(Generic[K, V]):
    """Internal skip list node."""
    __slots__ = ("key", "value", "forward")

    def __init__(self, key: Optional[K], value: Optional[V], level: int):
        self.key = key
        self.value = value
        self.forward: List[Optional[_Node[K, V]]] = [None] * (level + 1)


class SkipList(Generic[K, V]):
    """
    Probabilistic ordered map with O(log n) expected operations.

    Usage:
        sl = SkipList[str, int]()
        sl.insert("AAPL", 150)
        sl.search("AAPL")     # 150
        sl.delete("AAPL")     # True
        for k, v in sl.range_query("A", "B"):
            print(k, v)
    """

    def __init__(self):
        self._head: _Node[K, V] = _Node(None, None, _MAX_LEVEL)
        self._level = 0
        self._size = 0
        self._rng = random.Random()

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def _random_level(self) -> int:
        """Generate random level with geometric distribution (p=0.25)."""
        level = 0
        while self._rng.random() < _P and level < _MAX_LEVEL:
            level += 1
        return level

    def _find_update(self, key: K) -> List[Optional[_Node[K, V]]]:
        """Find the update path for a key."""
        update: List[Optional[_Node[K, V]]] = [None] * (_MAX_LEVEL + 1)
        current = self._head
        for i in range(self._level, -1, -1):
            while (current.forward[i] is not None and
                   current.forward[i].key is not None and  # type: ignore
                   current.forward[i].key < key):  # type: ignore
                current = current.forward[i]  # type: ignore
            update[i] = current
        return update

    def insert(self, key: K, value: V) -> None:
        """Insert or update a key-value pair. O(log n) expected."""
        update = self._find_update(key)
        current = update[0].forward[0] if update[0] else None  # type: ignore

        if current is not None and current.key == key:
            current.value = value
            return

        new_level = self._random_level()
        if new_level > self._level:
            for i in range(self._level + 1, new_level + 1):
                update[i] = self._head
            self._level = new_level

        new_node: _Node[K, V] = _Node(key, value, new_level)
        for i in range(new_level + 1):
            new_node.forward[i] = update[i].forward[i] if update[i] else None  # type: ignore
            if update[i]:
                update[i].forward[i] = new_node  # type: ignore

        self._size += 1

    def search(self, key: K) -> Optional[V]:
        """Search for a key. O(log n) expected."""
        current = self._head
        for i in range(self._level, -1, -1):
            while (current.forward[i] is not None and
                   current.forward[i].key is not None and  # type: ignore
                   current.forward[i].key < key):  # type: ignore
                current = current.forward[i]  # type: ignore

        current = current.forward[0]
        if current is not None and current.key == key:
            return current.value
        return None

    def delete(self, key: K) -> bool:
        """Delete a key. Returns True if key existed. O(log n) expected."""
        update = self._find_update(key)
        current = update[0].forward[0] if update[0] else None  # type: ignore

        if current is None or current.key != key:
            return False

        for i in range(self._level + 1):
            if update[i] and update[i].forward[i] == current:  # type: ignore
                update[i].forward[i] = current.forward[i]  # type: ignore

        while self._level > 0 and self._head.forward[self._level] is None:
            self._level -= 1

        self._size -= 1
        return True

    def contains(self, key: K) -> bool:
        """Check if key exists. O(log n) expected."""
        return self.search(key) is not None

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __getitem__(self, key: K) -> V:
        result = self.search(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: K, value: V) -> None:
        self.insert(key, value)

    def __delitem__(self, key: K) -> None:
        if not self.delete(key):
            raise KeyError(key)

    def range_query(self, lo: K, hi: K) -> Iterator[Tuple[K, V]]:
        """Iterate over key-value pairs in [lo, hi). O(log n + k)."""
        current = self._head
        for i in range(self._level, -1, -1):
            while (current.forward[i] is not None and
                   current.forward[i].key is not None and  # type: ignore
                   current.forward[i].key < lo):  # type: ignore
                current = current.forward[i]  # type: ignore

        current = current.forward[0]
        while current is not None and current.key is not None and current.key < hi:
            yield (current.key, current.value)  # type: ignore
            current = current.forward[0]

    def __iter__(self) -> Iterator[Tuple[K, V]]:
        """Iterate over all key-value pairs in sorted order."""
        current = self._head.forward[0]
        while current is not None and current.key is not None:
            yield (current.key, current.value)  # type: ignore
            current = current.forward[0]

    def min(self) -> Optional[Tuple[K, V]]:
        """Return the minimum key-value pair. O(1)."""
        node = self._head.forward[0]
        if node is not None and node.key is not None:
            return (node.key, node.value)  # type: ignore
        return None

    def max(self) -> Optional[Tuple[K, V]]:
        """Return the maximum key-value pair. O(n) worst case."""
        current = self._head
        while True:
            nxt = current.forward[0]
            if nxt is None or nxt.key is None:
                break
            current = nxt
        if current is not self._head:
            return (current.key, current.value)  # type: ignore
        return None

    def clear(self) -> None:
        """Remove all entries."""
        self._head = _Node(None, None, _MAX_LEVEL)
        self._level = 0
        self._size = 0
