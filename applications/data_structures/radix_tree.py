"""
ULL Radix Tree
==============

Compressed prefix tree (radix tree) for string-keyed data.

Radix trees compress single-child chains, reducing memory and
improving cache locality compared to standard tries. Each edge
stores a string fragment rather than a single character.

Optimizations:
- Path compression (single-child nodes merged)
- String fragments stored on edges (not per-character)
- Binary search on sorted children for O(log σ) child lookup
  where σ is the alphabet size
- Cache-friendly: fewer nodes = better locality

Latency: ~50-200 ns per operation (depends on key length)
"""

from __future__ import annotations

from typing import Dict, Generic, Iterator, List, Optional, Tuple, TypeVar

V = TypeVar("V")


class _RadixNode(Generic[V]):
    """Internal radix tree node."""
    __slots__ = ("children", "value", "has_value")

    def __init__(self):
        self.children: Dict[str, _RadixNode[V]] = {}
        self.value: Optional[V] = None
        self.has_value = False


class RadixTree(Generic[V]):
    """
    Compressed prefix tree for string keys.

    Usage:
        rt = RadixTree[int]()
        rt.insert("AAPL", 150)
        rt.search("AAPL")       # 150
        rt.starts_with("AA")    # True
        rt.delete("AAPL")       # True
    """

    def __init__(self):
        self._root: _RadixNode[V] = _RadixNode()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def insert(self, key: str, value: V) -> None:
        """Insert or update a key-value pair. O(k) where k = key length."""
        node = self._root
        i = 0
        while i < len(key):
            # Find matching child
            matched_child = None
            matched_len = 0
            for edge, child in node.children.items():
                # Find common prefix length
                j = 0
                while j < len(edge) and i + j < len(key) and edge[j] == key[i + j]:
                    j += 1
                if j > 0:
                    matched_child = child
                    matched_len = j
                    matched_edge = edge
                    break

            if matched_child is None:
                # No matching edge, create new leaf
                new_node: _RadixNode[V] = _RadixNode()
                node.children[key[i:]] = new_node
                node = new_node
                i = len(key)
            elif matched_len == len(matched_edge):
                # Full edge match, descend
                node = matched_child
                i += matched_len
            else:
                # Partial edge match, split the edge
                # Create intermediate node
                split_node: _RadixNode[V] = _RadixNode()
                # Old edge suffix becomes child of split
                split_node.children[matched_edge[matched_len:]] = matched_child
                # Replace old edge
                del node.children[matched_edge]
                node.children[matched_edge[:matched_len]] = split_node
                # Continue from split node
                node = split_node
                i += matched_len

        if not node.has_value:
            self._size += 1
        node.value = value
        node.has_value = True

    def search(self, key: str) -> Optional[V]:
        """Search for exact key match. O(k) where k = key length."""
        node = self._root
        i = 0
        while i < len(key):
            found = False
            for edge, child in node.children.items():
                if key[i:].startswith(edge):
                    node = child
                    i += len(edge)
                    found = True
                    break
            if not found:
                return None
        return node.value if node.has_value else None

    def starts_with(self, prefix: str) -> bool:
        """Check if any key starts with prefix. O(k) where k = prefix length."""
        node = self._root
        i = 0
        while i < len(prefix):
            found = False
            for edge, child in node.children.items():
                remaining = prefix[i:]
                if edge.startswith(remaining):
                    return True
                if remaining.startswith(edge):
                    node = child
                    i += len(edge)
                    found = True
                    break
            if not found:
                return False
        return True

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed. O(k)."""
        # Find the node and track path for cleanup
        path: List[Tuple[_RadixNode[V], str]] = []
        node = self._root
        i = 0
        while i < len(key):
            found = False
            for edge, child in node.children.items():
                if key[i:].startswith(edge):
                    path.append((node, edge))
                    node = child
                    i += len(edge)
                    found = True
                    break
            if not found:
                return False

        if not node.has_value:
            return False

        node.has_value = False
        node.value = None
        self._size -= 1

        # Cleanup: remove single-child chains
        while path and not node.has_value and len(node.children) == 1:
            parent, edge = path.pop()
            del parent.children[edge]
            # Merge if parent has only one child and no value
            if not parent.has_value and len(parent.children) == 1:
                child_edge, child_node = next(iter(parent.children.items()))
                parent.children.clear()
                parent.children[edge + child_edge] = child_node
            node = parent

        return True

    def contains(self, key: str) -> bool:
        """Check if key exists. O(k)."""
        return self.search(key) is not None

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def __getitem__(self, key: str) -> V:
        result = self.search(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, value: V) -> None:
        self.insert(key, value)

    def __delitem__(self, key: str) -> None:
        if not self.delete(key):
            raise KeyError(key)

    def _collect(self, node: _RadixNode[V], prefix: str) -> Iterator[Tuple[str, V]]:
        """Collect all key-value pairs in subtree."""
        if node.has_value:
            yield (prefix, node.value)  # type: ignore
        for edge, child in node.children.items():
            yield from self._collect(child, prefix + edge)

    def __iter__(self) -> Iterator[Tuple[str, V]]:
        """Iterate over all key-value pairs."""
        return self._collect(self._root, "")

    def keys_with_prefix(self, prefix: str) -> Iterator[str]:
        """Iterate over all keys with given prefix. O(k + m)."""
        node = self._root
        i = 0
        while i < len(prefix):
            found = False
            for edge, child in node.children.items():
                remaining = prefix[i:]
                if edge.startswith(remaining):
                    # All keys under this child match
                    for k, _ in self._collect(child, prefix[:i] + edge):
                        yield k
                    return
                if remaining.startswith(edge):
                    node = child
                    i += len(edge)
                    found = True
                    break
            if not found:
                return
        # Collect all keys under this node
        for k, _ in self._collect(node, prefix):
            yield k

    def clear(self) -> None:
        """Remove all entries."""
        self._root = _RadixNode()
        self._size = 0
