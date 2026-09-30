"""
ULL Data Structures Test Suite
==============================

Tests all data structure implementations for correctness.
"""

import sys
import os
import unittest

# Add project root to path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

from applications.data_structures import (
    RingBuffer,
    CircularArray,
    HashMap,
    SkipList,
    BTree,
    RadixTree,
    IntrusiveList,
    IntrusiveNode,
)


class TestRingBuffer(unittest.TestCase):
    def test_basic_push_pop(self):
        rb = RingBuffer[int](capacity=16)
        self.assertTrue(rb.is_empty())
        self.assertFalse(rb.is_full())

        self.assertTrue(rb.push(42))
        self.assertFalse(rb.is_empty())
        self.assertEqual(rb.size, 1)

        val = rb.pop()
        self.assertEqual(val, 42)
        self.assertTrue(rb.is_empty())

    def test_fifo_order(self):
        rb = RingBuffer[int](capacity=16)
        for i in range(10):
            self.assertTrue(rb.push(i))
        for i in range(10):
            self.assertEqual(rb.pop(), i)

    def test_full_buffer(self):
        rb = RingBuffer[int](capacity=16)
        # Fill to capacity - 1 (one slot reserved for full/empty distinction)
        for i in range(15):
            self.assertTrue(rb.push(i))
        self.assertTrue(rb.is_full())
        self.assertFalse(rb.push(999))  # should fail

    def test_wrap_around(self):
        rb = RingBuffer[int](capacity=16)
        # Push and pop to advance head/tail
        for i in range(20):
            rb.push(i)
            rb.pop()
        # Now push more to test wrap-around
        for i in range(10):
            self.assertTrue(rb.push(i))
        for i in range(10):
            self.assertEqual(rb.pop(), i)

    def test_batch_operations(self):
        rb = RingBuffer[int](capacity=16)
        items = list(range(10))
        n = rb.push_batch(items)
        self.assertEqual(n, 10)
        self.assertEqual(rb.size, 10)

        result = rb.pop_batch(5)
        self.assertEqual(result, [0, 1, 2, 3, 4])
        self.assertEqual(rb.size, 5)


class TestCircularArray(unittest.TestCase):
    def test_push_back(self):
        ca = CircularArray[int]()
        ca.push_back(1)
        ca.push_back(2)
        ca.push_back(3)
        self.assertEqual(len(ca), 3)
        self.assertEqual(ca[0], 1)
        self.assertEqual(ca[1], 2)
        self.assertEqual(ca[2], 3)

    def test_push_front(self):
        ca = CircularArray[int]()
        ca.push_front(1)
        ca.push_front(2)
        ca.push_front(3)
        self.assertEqual(ca[0], 3)
        self.assertEqual(ca[1], 2)
        self.assertEqual(ca[2], 1)

    def test_pop_back(self):
        ca = CircularArray[int]()
        ca.push_back(1)
        ca.push_back(2)
        self.assertEqual(ca.pop_back(), 2)
        self.assertEqual(ca.pop_back(), 1)
        self.assertIsNone(ca.pop_back())

    def test_pop_front(self):
        ca = CircularArray[int]()
        ca.push_back(1)
        ca.push_back(2)
        self.assertEqual(ca.pop_front(), 1)
        self.assertEqual(ca.pop_front(), 2)
        self.assertIsNone(ca.pop_front())

    def test_growth(self):
        ca = CircularArray[int](capacity=4)
        for i in range(100):
            ca.push_back(i)
        self.assertEqual(len(ca), 100)
        for i in range(100):
            self.assertEqual(ca[i], i)

    def test_iteration(self):
        ca = CircularArray[int]()
        for i in range(10):
            ca.push_back(i)
        self.assertEqual(list(ca), list(range(10)))

    def test_mixed_operations(self):
        ca = CircularArray[int]()
        ca.push_back(2)
        ca.push_front(1)
        ca.push_back(3)
        self.assertEqual(list(ca), [1, 2, 3])
        ca.pop_front()
        ca.pop_back()
        self.assertEqual(list(ca), [2])


class TestHashMap(unittest.TestCase):
    def test_basic_put_get(self):
        hm = HashMap[str, int]()
        hm.put("AAPL", 150)
        self.assertEqual(hm.get("AAPL"), 150)
        self.assertEqual(hm["AAPL"], 150)

    def test_update(self):
        hm = HashMap[str, int]()
        hm.put("AAPL", 150)
        hm.put("AAPL", 200)
        self.assertEqual(hm.get("AAPL"), 200)
        self.assertEqual(len(hm), 1)

    def test_remove(self):
        hm = HashMap[str, int]()
        hm.put("AAPL", 150)
        self.assertTrue(hm.remove("AAPL"))
        self.assertIsNone(hm.get("AAPL"))
        self.assertFalse(hm.remove("AAPL"))

    def test_contains(self):
        hm = HashMap[str, int]()
        hm.put("AAPL", 150)
        self.assertIn("AAPL", hm)
        self.assertNotIn("GOOG", hm)

    def test_growth(self):
        hm = HashMap[int, int]()
        for i in range(1000):
            hm.put(i, i * 2)
        self.assertEqual(len(hm), 1000)
        for i in range(1000):
            self.assertEqual(hm.get(i), i * 2)

    def test_iteration(self):
        hm = HashMap[str, int]()
        hm.put("a", 1)
        hm.put("b", 2)
        items = dict(hm.items())
        self.assertEqual(items, {"a": 1, "b": 2})

    def test_clear(self):
        hm = HashMap[str, int]()
        hm.put("a", 1)
        hm.clear()
        self.assertEqual(len(hm), 0)
        self.assertIsNone(hm.get("a"))


class TestSkipList(unittest.TestCase):
    def test_insert_search(self):
        sl = SkipList[str, int]()
        sl.insert("AAPL", 150)
        self.assertEqual(sl.search("AAPL"), 150)
        self.assertEqual(sl["AAPL"], 150)

    def test_update(self):
        sl = SkipList[str, int]()
        sl.insert("AAPL", 150)
        sl.insert("AAPL", 200)
        self.assertEqual(sl.search("AAPL"), 200)
        self.assertEqual(len(sl), 1)

    def test_delete(self):
        sl = SkipList[str, int]()
        sl.insert("AAPL", 150)
        self.assertTrue(sl.delete("AAPL"))
        self.assertIsNone(sl.search("AAPL"))
        self.assertFalse(sl.delete("AAPL"))

    def test_ordered_iteration(self):
        sl = SkipList[int, int]()
        keys = [5, 2, 8, 1, 9, 3]
        for k in keys:
            sl.insert(k, k * 10)
        self.assertEqual([k for k, _ in sl], sorted(keys))

    def test_range_query(self):
        sl = SkipList[int, int]()
        for i in range(100):
            sl.insert(i, i * 10)
        result = list(sl.range_query(10, 20))
        self.assertEqual([k for k, _ in result], list(range(10, 20)))

    def test_min_max(self):
        sl = SkipList[int, int]()
        sl.insert(5, 50)
        sl.insert(2, 20)
        sl.insert(8, 80)
        self.assertEqual(sl.min(), (2, 20))
        self.assertEqual(sl.max(), (8, 80))


class TestBTree(unittest.TestCase):
    def test_insert_search(self):
        bt = BTree[str, int](degree=4)
        bt.insert("AAPL", 150)
        self.assertEqual(bt.search("AAPL"), 150)
        self.assertEqual(bt["AAPL"], 150)

    def test_update(self):
        bt = BTree[str, int](degree=4)
        bt.insert("AAPL", 150)
        bt.insert("AAPL", 200)
        self.assertEqual(bt.search("AAPL"), 200)
        self.assertEqual(len(bt), 1)

    def test_delete(self):
        bt = BTree[str, int](degree=4)
        bt.insert("AAPL", 150)
        self.assertTrue(bt.delete("AAPL"))
        self.assertIsNone(bt.search("AAPL"))
        self.assertFalse(bt.delete("AAPL"))

    def test_ordered_iteration(self):
        bt = BTree[int, int](degree=4)
        keys = [5, 2, 8, 1, 9, 3, 7, 4, 6]
        for k in keys:
            bt.insert(k, k * 10)
        self.assertEqual([k for k, _ in bt], sorted(keys))

    def test_range_query(self):
        bt = BTree[int, int](degree=4)
        for i in range(100):
            bt.insert(i, i * 10)
        result = list(bt.range_query(10, 20))
        self.assertEqual([k for k, _ in result], list(range(10, 20)))

    def test_min_max(self):
        bt = BTree[int, int](degree=4)
        bt.insert(5, 50)
        bt.insert(2, 20)
        bt.insert(8, 80)
        self.assertEqual(bt.min(), (2, 20))
        self.assertEqual(bt.max(), (8, 80))

    def test_large_insert(self):
        bt = BTree[int, int](degree=8)
        for i in range(1000):
            bt.insert(i, i * 2)
        self.assertEqual(len(bt), 1000)
        for i in range(1000):
            self.assertEqual(bt.search(i), i * 2)


class TestRadixTree(unittest.TestCase):
    def test_insert_search(self):
        rt = RadixTree[int]()
        rt.insert("AAPL", 150)
        self.assertEqual(rt.search("AAPL"), 150)
        self.assertEqual(rt["AAPL"], 150)

    def test_prefix_search(self):
        rt = RadixTree[int]()
        rt.insert("AAPL", 150)
        rt.insert("AAP", 100)
        rt.insert("GOOG", 200)
        self.assertTrue(rt.starts_with("AA"))
        self.assertTrue(rt.starts_with("AAPL"))
        self.assertTrue(rt.starts_with("GO"))

    def test_delete(self):
        rt = RadixTree[int]()
        rt.insert("AAPL", 150)
        self.assertTrue(rt.delete("AAPL"))
        self.assertIsNone(rt.search("AAPL"))
        self.assertFalse(rt.delete("AAPL"))

    def test_keys_with_prefix(self):
        rt = RadixTree[int]()
        rt.insert("AAPL", 150)
        rt.insert("AAP", 100)
        rt.insert("GOOG", 200)
        result = sorted(rt.keys_with_prefix("AA"))
        self.assertEqual(result, ["AAP", "AAPL"])

    def test_shared_prefix(self):
        rt = RadixTree[int]()
        rt.insert("romane", 1)
        rt.insert("romanus", 2)
        rt.insert("romulus", 3)
        rt.insert("rubens", 4)
        rt.insert("ruber", 5)
        self.assertEqual(rt.search("romane"), 1)
        self.assertEqual(rt.search("romanus"), 2)
        self.assertEqual(rt.search("rubens"), 4)
        self.assertEqual(rt.search("ruber"), 5)


class TestIntrusiveList(unittest.TestCase):
    def test_push_back(self):
        class Item(IntrusiveNode):
            def __init__(self, val):
                super().__init__()
                self.val = val

        il = IntrusiveList[Item]()
        il.push_back(Item(1))
        il.push_back(Item(2))
        il.push_back(Item(3))
        self.assertEqual(len(il), 3)
        self.assertEqual([n.val for n in il], [1, 2, 3])

    def test_push_front(self):
        class Item(IntrusiveNode):
            def __init__(self, val):
                super().__init__()
                self.val = val

        il = IntrusiveList[Item]()
        il.push_front(Item(1))
        il.push_front(Item(2))
        self.assertEqual([n.val for n in il], [2, 1])

    def test_pop_back(self):
        class Item(IntrusiveNode):
            def __init__(self, val):
                super().__init__()
                self.val = val

        il = IntrusiveList[Item]()
        il.push_back(Item(1))
        il.push_back(Item(2))
        node = il.pop_back()
        self.assertIsNotNone(node)
        self.assertEqual(node.val, 2)
        self.assertEqual(len(il), 1)

    def test_pop_front(self):
        class Item(IntrusiveNode):
            def __init__(self, val):
                super().__init__()
                self.val = val

        il = IntrusiveList[Item]()
        il.push_back(Item(1))
        il.push_back(Item(2))
        node = il.pop_front()
        self.assertIsNotNone(node)
        self.assertEqual(node.val, 1)
        self.assertEqual(len(il), 1)

    def test_remove_node(self):
        class Item(IntrusiveNode):
            def __init__(self, val):
                super().__init__()
                self.val = val

        il = IntrusiveList[Item]()
        n1 = Item(1)
        n2 = Item(2)
        n3 = Item(3)
        il.push_back(n1)
        il.push_back(n2)
        il.push_back(n3)
        self.assertTrue(il.remove(n2))
        self.assertEqual([n.val for n in il], [1, 3])
        self.assertFalse(il.remove(n2))  # already removed

    def test_insert_after(self):
        class Item(IntrusiveNode):
            def __init__(self, val):
                super().__init__()
                self.val = val

        il = IntrusiveList[Item]()
        n1 = Item(1)
        n2 = Item(2)
        il.push_back(n1)
        il.push_back(n2)
        n3 = Item(3)
        il.insert_after(n1, n3)
        self.assertEqual([n.val for n in il], [1, 3, 2])

    def test_reversed_iteration(self):
        class Item(IntrusiveNode):
            def __init__(self, val):
                super().__init__()
                self.val = val

        il = IntrusiveList[Item]()
        for i in range(5):
            il.push_back(Item(i))
        self.assertEqual([n.val for n in reversed(il)], [4, 3, 2, 1, 0])


if __name__ == "__main__":
    unittest.main()
