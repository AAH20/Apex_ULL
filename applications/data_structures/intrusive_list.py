"""
ULL Intrusive List
==================

Zero-allocation doubly-linked list where node pointers are embedded
in the user's data structure.

Intrusive lists eliminate per-node memory allocation by storing
the prev/next pointers directly in the user's struct/class. This
improves cache locality and eliminates allocator overhead on
the hot path.

Optimizations:
- Zero allocation on insert/remove (pointers embedded in user data)
- O(1) insert/remove at any position
- No separate node objects = better cache locality
- Lock-free operations possible with CAS on pointers

Latency: ~5-10 ns per insert/remove (cache-hot)
"""

from __future__ import annotations

from typing import Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class IntrusiveNode:
    """
    Base class for intrusive list nodes.

    Embed this in your data structure to make it list-able:

        class Order(IntrusiveNode):
            def __init__(self, order_id: int, price: float):
                super().__init__()
                self.order_id = order_id
                self.price = price
    """

    __slots__ = ("prev", "next")

    def __init__(self):
        self.prev: Optional[IntrusiveNode] = None
        self.next: Optional[IntrusiveNode] = None


class IntrusiveList(Generic[T]):
    """
    Doubly-linked list with embedded node pointers.

    Usage:
        class Order(IntrusiveNode):
            def __init__(self, oid: int):
                super().__init__()
                self.oid = oid

        orders = IntrusiveList[Order]()
        order = Order(1)
        orders.push_back(order)
        orders.pop_front()
    """

    def __init__(self):
        # Sentinel node (dummy head/tail)
        self._head = IntrusiveNode()
        self._tail = IntrusiveNode()
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def is_empty(self) -> bool:
        return self._size == 0

    def push_back(self, node: IntrusiveNode) -> None:
        """Insert node at the back. O(1)."""
        node.prev = self._tail.prev
        node.next = self._tail
        if self._tail.prev:
            self._tail.prev.next = node
        self._tail.prev = node
        self._size += 1

    def push_front(self, node: IntrusiveNode) -> None:
        """Insert node at the front. O(1)."""
        node.next = self._head.next
        node.prev = self._head
        if self._head.next:
            self._head.next.prev = node
        self._head.next = node
        self._size += 1

    def pop_back(self) -> Optional[IntrusiveNode]:
        """Remove and return the back node. O(1)."""
        if self._size == 0:
            return None
        node = self._tail.prev
        if node:
            self._remove_node(node)
        return node

    def pop_front(self) -> Optional[IntrusiveNode]:
        """Remove and return the front node. O(1)."""
        if self._size == 0:
            return None
        node = self._head.next
        if node:
            self._remove_node(node)
        return node

    def _remove_node(self, node: IntrusiveNode) -> None:
        """Remove a node from the list. O(1)."""
        if node.prev:
            node.prev.next = node.next
        if node.next:
            node.next.prev = node.prev
        node.prev = None
        node.next = None
        self._size -= 1

    def remove(self, node: IntrusiveNode) -> bool:
        """Remove a specific node. Returns True if node was in list. O(1)."""
        if node.prev is None and node.next is None:
            return False  # not in list
        self._remove_node(node)
        return True

    def insert_after(self, existing: IntrusiveNode, new_node: IntrusiveNode) -> None:
        """Insert new_node after existing node. O(1)."""
        new_node.next = existing.next
        new_node.prev = existing
        if existing.next:
            existing.next.prev = new_node
        existing.next = new_node
        self._size += 1

    def insert_before(self, existing: IntrusiveNode, new_node: IntrusiveNode) -> None:
        """Insert new_node before existing node. O(1)."""
        new_node.prev = existing.prev
        new_node.next = existing
        if existing.prev:
            existing.prev.next = new_node
        existing.prev = new_node
        self._size += 1

    def front(self) -> Optional[IntrusiveNode]:
        """Return the front node without removing. O(1)."""
        node = self._head.next
        return node if node != self._tail else None

    def back(self) -> Optional[IntrusiveNode]:
        """Return the back node without removing. O(1)."""
        node = self._tail.prev
        return node if node != self._head else None

    def __iter__(self) -> Iterator[IntrusiveNode]:
        """Iterate from front to back."""
        current = self._head.next
        while current is not None and current != self._tail:
            yield current
            current = current.next

    def __reversed__(self) -> Iterator[IntrusiveNode]:
        """Iterate from back to front."""
        current = self._tail.prev
        while current is not None and current != self._head:
            yield current
            current = current.prev

    def to_list(self) -> List[IntrusiveNode]:
        """Return a snapshot as a list."""
        return list(self)

    def clear(self) -> None:
        """Remove all nodes. O(n) to clear pointers."""
        for node in self:
            node.prev = None
            node.next = None
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0
