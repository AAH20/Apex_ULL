"""
Minimum Spanning Tree (MST)
============================

Problem Definition
------------------
Given a connected, undirected graph G = (V, E) with edge weights w: E -> R+,
find a spanning tree T ⊆ E that connects all vertices with minimum total
edge weight:

    w(T) = sum_{e in T} w(e)

The MST is fundamental in network design for ULL systems:
- **Topology synthesis** — build minimal-cost interconnects
- **Broadcast routing** — MST minimizes total link cost for multicast
- **Fault-tolerant overlay** — MST + k extra edges for k-resilience
- **Clustering** — MST edges define natural cluster boundaries

Algorithms
----------
1. **Kruskal's** — O(E log E) via union-find with path compression
2. **Prim's** — O(E log V) via binary heap (dense: O(V²))

Latency Impact
--------------
- MST minimizes total wire length → lower propagation delay
- Fewer active links → lower power, fewer failure points
- MST diameter can be large; use +k edges for bounded diameter
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import heapq

import networkx as nx
import numpy as np


@dataclass
class MSTResult:
    """Result of a minimum spanning tree computation."""
    edges: list[tuple]
    total_weight: float
    algorithm: str
    num_edges: int = 0
    metadata: dict = field(default_factory=dict)


class UnionFind:
    """Union-Find (Disjoint Set Union) with path compression and union by rank."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        """Find root with path compression."""
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> bool:
        """Union by rank. Returns True if merged, False if already connected."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True


def kruskal_mst(
    graph: nx.Graph,
    weight: str = "weight",
) -> MSTResult:
    """
    Kruskal's algorithm for minimum spanning tree.

    Sorts all edges by weight and greedily adds the lightest edge that
    does not create a cycle, using union-find for cycle detection.

    Time complexity: O(E log E) dominated by sorting.
    Space complexity: O(V + E).

    Parameters
    ----------
    graph : nx.Graph
        Input undirected graph with edge weights.
    weight : str
        Edge attribute to use as weight.

    Returns
    -------
    MSTResult
        The MST edges and total weight.
    """
    if graph.is_directed():
        raise ValueError("Kruskal's requires an undirected graph")

    nodes = list(graph.nodes())
    n = len(nodes)
    if n == 0:
        return MSTResult(edges=[], total_weight=0.0, algorithm="kruskal", num_edges=0)
    if n == 1:
        return MSTResult(edges=[], total_weight=0.0, algorithm="kruskal", num_edges=0)

    node_to_idx = {node: i for i, node in enumerate(nodes)}

    # Collect and sort edges by weight
    edges: list[tuple[float, Any, Any, dict]] = []
    for u, v, data in graph.edges(data=True):
        w = data.get(weight, 1.0)
        edges.append((w, u, v, data))
    edges.sort(key=lambda x: x[0])

    uf = UnionFind(n)
    mst_edges: list[tuple] = []
    total_weight = 0.0

    for w, u, v, data in edges:
        ui, vi = node_to_idx[u], node_to_idx[v]
        if uf.union(ui, vi):
            mst_edges.append((u, v))
            total_weight += w
            if len(mst_edges) == n - 1:
                break

    return MSTResult(
        edges=mst_edges,
        total_weight=float(total_weight),
        algorithm="kruskal",
        num_edges=len(mst_edges),
        metadata={"nodes": n, "edges_considered": len(edges)},
    )


def prim_mst(
    graph: nx.Graph,
    weight: str = "weight",
    start: Any = None,
) -> MSTResult:
    """
    Prim's algorithm for minimum spanning tree.

    Grows the MST from a starting node by always adding the lightest
    edge connecting the tree to a non-tree vertex. Uses a binary heap
    for efficient minimum-edge extraction.

    Time complexity: O(E log V) with binary heap.
    Space complexity: O(V + E).

    Parameters
    ----------
    graph : nx.Graph
        Input undirected graph with edge weights.
    weight : str
        Edge attribute to use as weight.
    start : node, optional
        Starting node. If None, picks an arbitrary node.

    Returns
    -------
    MSTResult
        The MST edges and total weight.
    """
    if graph.is_directed():
        raise ValueError("Prim's requires an undirected graph")

    nodes = list(graph.nodes())
    n = len(nodes)
    if n == 0:
        return MSTResult(edges=[], total_weight=0.0, algorithm="prim", num_edges=0)
    if n == 1:
        return MSTResult(edges=[], total_weight=0.0, algorithm="prim", num_edges=0)

    if start is None:
        start = nodes[0]

    in_tree: set = set()
    mst_edges: list[tuple] = []
    total_weight = 0.0

    # Min-heap: (weight, counter, from_node, to_node, edge_data)
    counter = 0
    heap: list[tuple[float, int, Any, Any, dict]] = []

    def add_edges(node):
        nonlocal counter
        for neighbor, data in graph[node].items():
            if neighbor not in in_tree:
                w = data.get(weight, 1.0)
                heapq.heappush(heap, (w, counter, node, neighbor, data))
                counter += 1

    in_tree.add(start)
    add_edges(start)

    while heap and len(in_tree) < n:
        w, _, u, v, data = heapq.heappop(heap)
        if v in in_tree:
            continue
        in_tree.add(v)
        mst_edges.append((u, v))
        total_weight += w
        add_edges(v)

    return MSTResult(
        edges=mst_edges,
        total_weight=float(total_weight),
        algorithm="prim",
        num_edges=len(mst_edges),
        metadata={"nodes": n, "start": start},
    )


def mst_to_graph(graph: nx.Graph, mst_result: MSTResult) -> nx.Graph:
    """
    Convert MST result to a NetworkX graph.

    Parameters
    ----------
    graph : nx.Graph
        Original graph (for node attributes).
    mst_result : MSTResult
        Result from kruskal_mst or prim_mst.

    Returns
    -------
    nx.Graph
        A graph containing only the MST edges with original weights.
    """
    mst_graph = nx.Graph()
    for node in graph.nodes():
        mst_graph.add_node(node, **graph.nodes[node])
    for u, v in mst_result.edges:
        data = graph.get_edge_data(u, v)
        mst_graph.add_edge(u, v, **data)
    return mst_graph


def mst_diameter(mst_graph: nx.Graph) -> int:
    """
    Compute the diameter (longest shortest path) of an MST.

    Parameters
    ----------
    mst_graph : nx.Graph
        The MST graph.

    Returns
    -------
    int
        Diameter of the tree.
    """
    if len(mst_graph) <= 1:
        return 0
    lengths = dict(nx.all_pairs_shortest_path_length(mst_graph))
    return max(max(d.values()) for d in lengths.values())


def mst_max_edge_latency(mst_graph: nx.Graph, latency_attr: str = "latency") -> float:
    """
    Find the maximum edge latency in the MST (bottleneck edge).

    Parameters
    ----------
    mst_graph : nx.Graph
        The MST graph.
    latency_attr : str
        Edge attribute for latency.

    Returns
    -------
    float
        Maximum edge latency.
    """
    if mst_graph.number_of_edges() == 0:
        return 0.0
    return max(data.get(latency_attr, 0.0) for _, _, data in mst_graph.edges(data=True))
