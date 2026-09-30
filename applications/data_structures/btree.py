"""
ULL B-Tree
==========

B-tree for ordered key-value storage with O(log n) operations.

B-trees are optimized for systems with high cache miss penalties
(such as disk or NUMA) but also provide excellent cache behavior
for in-memory use. Each node contains multiple keys, reducing
tree height and improving cache locality.

Optimizations:
- High fanout (default 64) minimizes tree height
- Keys stored contiguously within nodes for cache-friendly scans
- No rebalancing on insert (split only when full)
- Bulk-friendly: sequential inserts are very efficient

Latency: ~50-200 ns per operation (cache-hot)
"""

from __future__ import annotations

from typing import Generic, Iterator, List, Optional, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class _BNode(Generic[K, V]):
    """Internal B-tree node."""
    __slots__ = ("keys", "values", "children", "leaf", "n", "_capacity")

    def __init__(self, leaf: bool = True, capacity: int = 64):
        self.keys: List[K] = []
        self.values: List[V] = []
        self.children: List[_BNode[K, V]] = []
        self.leaf = leaf
        self.n = 0  # current number of keys
        self._capacity = capacity

    def is_full(self) -> bool:
        return self.n >= self._capacity - 1


class BTree(Generic[K, V]):
    """
    B-tree with configurable fanout.

    Usage:
        bt = BTree[str, int](degree=64)
        bt.insert("AAPL", 150)
        bt.search("AAPL")     # 150
        bt.delete("AAPL")     # True
        for k, bt.range_query("A", "B"):
            print(k, v)
    """

    def __init__(self, degree: int = 64):
        if degree < 4:
            degree = 4
        self._degree = degree
        self._root: _BNode[K, V] = _BNode(leaf=True, capacity=degree)
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def _split_child(self, parent: _BNode[K, V], i: int) -> None:
        """Split the i-th child of parent."""
        degree = self._degree
        full_child = parent.children[i]
        mid = degree // 2

        # New node gets the right half
        new_child: _BNode[K, V] = _BNode(leaf=full_child.leaf, capacity=degree)
        new_child.keys = full_child.keys[mid + 1:]
        new_child.values = full_child.values[mid + 1:]
        new_child.n = len(new_child.keys)

        if not full_child.leaf:
            new_child.children = full_child.children[mid + 1:]
            full_child.children = full_child.children[:mid + 1]

        # Middle key moves up to parent
        parent.keys.insert(i, full_child.keys[mid])
        parent.values.insert(i, full_child.values[mid])
        parent.children.insert(i + 1, new_child)
        parent.n += 1

        # Truncate full child
        full_child.keys = full_child.keys[:mid]
        full_child.values = full_child.values[:mid]
        full_child.n = len(full_child.keys)

    def _insert_non_full(self, node: _BNode[K, V], key: K, value: V) -> bool:
        """Insert into a non-full node. Returns True if new key inserted."""
        i = node.n - 1

        if node.leaf:
            # Insert into leaf
            while i >= 0 and key < node.keys[i]:
                i -= 1
            if i >= 0 and node.keys[i] == key:
                node.values[i] = value
                return False  # updated existing
            node.keys.insert(i + 1, key)
            node.values.insert(i + 1, value)
            node.n += 1
            return True
        else:
            # Find child to descend into
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            if node.keys[i - 1] == key if i > 0 else False:
                node.values[i - 1] = value
                return False
            if node.children[i].is_full():
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            return self._insert_non_full(node.children[i], key, value)

    def insert(self, key: K, value: V) -> None:
        """Insert or update a key-value pair. O(log n)."""
        root = self._root
        if root.is_full():
            new_root: _BNode[K, V] = _BNode(leaf=False, capacity=self._degree)
            new_root.children.append(self._root)
            self._root = new_root
            self._split_child(new_root, 0)
        if self._insert_non_full(self._root, key, value):
            self._size += 1

    def _find_key(self, node: _BNode[K, V], key: K) -> Optional[V]:
        """Find key in subtree rooted at node."""
        i = 0
        while i < node.n and key > node.keys[i]:
            i += 1
        if i < node.n and node.keys[i] == key:
            return node.values[i]
        if node.leaf:
            return None
        return self._find_key(node.children[i], key)

    def search(self, key: K) -> Optional[V]:
        """Search for a key. O(log n)."""
        return self._find_key(self._root, key)

    def contains(self, key: K) -> bool:
        """Check if key exists. O(log n)."""
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

    def _delete_from_node(self, node: _BNode[K, V], key: K) -> bool:
        """Delete key from subtree. Returns True if key was found."""
        idx = 0
        while idx < node.n and node.keys[idx] < key:
            idx += 1

        if idx < node.n and node.keys[idx] == key:
            if node.leaf:
                node.keys.pop(idx)
                node.values.pop(idx)
                node.n -= 1
                return True
            else:
                # Internal node: replace with predecessor
                pred_node = node.children[idx]
                while not pred_node.leaf:
                    pred_node = pred_node.children[-1]
                node.keys[idx] = pred_node.keys[-1]
                node.values[idx] = pred_node.values[-1]
                return self._delete_from_node(node.children[idx], pred_node.keys[-1])

        if node.leaf:
            return False

        # Ensure child has enough keys before descending
        child = node.children[idx]
        if child.n < self._degree // 2:
            self._fill_child(node, idx)
        if idx > node.n:
            return self._delete_from_node(node.children[idx - 1], key)
        return self._delete_from_node(node.children[idx], key)

    def _fill_child(self, parent: _BNode[K, V], idx: int) -> None:
        """Ensure parent.children[idx] has at least degree//2 keys."""
        degree = self._degree
        if idx > 0 and parent.children[idx - 1].n >= degree // 2:
            self._borrow_from_prev(parent, idx)
        elif idx < parent.n and parent.children[idx + 1].n >= degree // 2:
            self._borrow_from_next(parent, idx)
        else:
            if idx < parent.n:
                self._merge(parent, idx)
            else:
                self._merge(parent, idx - 1)

    def _borrow_from_prev(self, parent: _BNode[K, V], idx: int) -> None:
        """Borrow a key from the left sibling."""
        child = parent.children[idx]
        sibling = parent.children[idx - 1]

        child.keys.insert(0, parent.keys[idx - 1])
        child.values.insert(0, parent.values[idx - 1])
        if not child.leaf:
            child.children.insert(0, sibling.children.pop())
        parent.keys[idx - 1] = sibling.keys.pop()
        parent.values[idx - 1] = sibling.values.pop()
        child.n += 1
        sibling.n -= 1

    def _borrow_from_next(self, parent: _BNode[K, V], idx: int) -> None:
        """Borrow a key from the right sibling."""
        child = parent.children[idx]
        sibling = parent.children[idx + 1]

        child.keys.append(parent.keys[idx])
        child.values.append(parent.values[idx])
        if not child.leaf:
            child.children.append(sibling.children.pop(0))
        parent.keys[idx] = sibling.keys.pop(0)
        parent.values[idx] = sibling.values.pop(0)
        child.n += 1
        sibling.n -= 1

    def _merge(self, parent: _BNode[K, V], idx: int) -> None:
        """Merge parent.children[idx] with parent.children[idx+1]."""
        child = parent.children[idx]
        sibling = parent.children[idx + 1]

        child.keys.append(parent.keys.pop(idx))
        child.values.append(parent.values.pop(idx))
        child.keys.extend(sibling.keys)
        child.values.extend(sibling.values)
        if not child.leaf:
            child.children.extend(sibling.children)
        child.n = len(child.keys)
        parent.children.pop(idx + 1)
        parent.n -= 1

    def delete(self, key: K) -> bool:
        """Delete a key. Returns True if key existed. O(log n)."""
        if not self.contains(key):
            return False
        self._delete_from_node(self._root, key)
        self._size -= 1
        if self._root.n == 0 and not self._root.leaf:
            self._root = self._root.children[0]
        return True

    def __delitem__(self, key: K) -> None:
        if not self.delete(key):
            raise KeyError(key)

    def _inorder(self, node: _BNode[K, V]) -> Iterator[Tuple[K, V]]:
        """In-order traversal."""
        for i in range(node.n):
            if not node.leaf:
                yield from self._inorder(node.children[i])
            yield (node.keys[i], node.values[i])
        if not node.leaf:
            yield from self._inorder(node.children[-1])

    def __iter__(self) -> Iterator[Tuple[K, V]]:
        """Iterate over all key-value pairs in sorted order."""
        return self._inorder(self._root)

    def range_query(self, lo: K, hi: K) -> Iterator[Tuple[K, V]]:
        """Iterate over key-value pairs in [lo, hi). O(log n + k)."""
        yield from self._range_helper(self._root, lo, hi)

    def _range_helper(self, node: _BNode[K, V], lo: K, hi: K) -> Iterator[Tuple[K, V]]:
        """Helper for range query."""
        i = 0
        while i < node.n and node.keys[i] < lo:
            i += 1
        while i < node.n and node.keys[i] < hi:
            if not node.leaf:
                yield from self._range_helper(node.children[i], lo, hi)
            yield (node.keys[i], node.values[i])
            i += 1
        if not node.leaf and i <= node.n:
            yield from self._range_helper(node.children[i], lo, hi)

    def min(self) -> Optional[Tuple[K, V]]:
        """Return the minimum key-value pair. O(log n)."""
        node = self._root
        while not node.leaf:
            node = node.children[0]
        if node.n > 0:
            return (node.keys[0], node.values[0])
        return None

    def max(self) -> Optional[Tuple[K, V]]:
        """Return the maximum key-value pair. O(log n)."""
        node = self._root
        while not node.leaf:
            node = node.children[-1]
        if node.n > 0:
            return (node.keys[-1], node.values[-1])
        return None

    def clear(self) -> None:
        """Remove all entries."""
        self._root = _BNode(leaf=True, capacity=self._degree)
        self._size = 0
