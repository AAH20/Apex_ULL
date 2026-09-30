"""
Maximum Flow (MaxFlow)
=======================

Problem Definition
------------------
Given a directed graph G = (V, E) with edge capacities c: E -> R+, a source
node s, and a sink node t, find a flow f: E -> R+ that maximizes the total
flow from s to t subject to:

1. **Capacity constraint:** 0 ≤ f(e) ≤ c(e) for all e in E
2. **Flow conservation:** sum_{e into v} f(e) = sum_{e out of v} f(e) for all v ∉ {s, t}

The maximum flow value equals the minimum cut capacity (Max-Flow Min-Cut Theorem).

Algorithms
----------
1. **Edmonds-Karp** — O(V · E²) BFS-based augmenting paths
2. **Dinic's** — O(V² · E) with level graphs and blocking flows

Latency Impact
--------------
- MaxFlow determines worst-case network throughput between endpoints
- Min-cut identifies network bottlenecks for capacity planning
- Multi-commodity flow models concurrent traffic in ULL interconnects
- Flow decomposition gives explicit routing paths for traffic engineering
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import numpy as np


@dataclass
class MaxFlowResult:
    """Result of a maximum flow computation."""
    flow_value: float
    flow_dict: dict
    algorithm: str
    source: Any
    sink: Any
    num_augmentations: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class MinCutResult:
    """Result of a minimum cut computation."""
    cut_value: float
    partition_source: set
    partition_sink: set
    cut_edges: list[tuple]
    algorithm: str
    metadata: dict = field(default_factory=dict)


def _build_capacity_graph(
    graph: nx.DiGraph,
    capacity: str,
    source: Any,
    sink: Any,
) -> tuple[dict, dict, dict]:
    """
    Build internal capacity and adjacency structures.

    Returns
    -------
    cap : dict
        cap[u][v] = residual capacity from u to v.
    adj : dict
        adj[u] = set of neighbors (both directions for residual).
    orig_cap : dict
        Original capacities.
    """
    cap: dict[Any, dict[Any, float]] = {}
    adj: dict[Any, set] = {}
    orig_cap: dict[Any, dict[Any, float]] = {}

    for u in graph.nodes():
        cap[u] = {}
        adj[u] = set()
        orig_cap[u] = {}

    for u, v, data in graph.edges(data=True):
        c = data.get(capacity, 1.0)
        cap[u][v] = cap[u].get(v, 0.0) + c
        adj[u].add(v)
        adj[v].add(u)  # residual backward edge
        orig_cap[u][v] = orig_cap[u].get(v, 0.0) + c

    return cap, adj, orig_cap


def edmonds_karp(
    graph: nx.DiGraph,
    source: Any,
    sink: Any,
    capacity: str = "capacity",
) -> MaxFlowResult:
    """
    Edmonds-Karp algorithm for maximum flow.

    Repeatedly finds the shortest augmenting path via BFS and pushes
    flow along it. Guarantees O(V · E²) time complexity.

    Parameters
    ----------
    graph : nx.DiGraph
        Input directed graph with edge capacities.
    source : node
        Source node.
    sink : node
        Sink node.
    capacity : str
        Edge attribute to use as capacity.

    Returns
    -------
    MaxFlowResult
        The maximum flow value and flow assignment.
    """
    if source not in graph or sink not in graph:
        raise ValueError("Source or sink not in graph")
    if source == sink:
        raise ValueError("Source and sink must be different")

    cap, adj, orig_cap = _build_capacity_graph(graph, capacity, source, sink)

    flow_value = 0.0
    num_aug = 0

    while True:
        # BFS for shortest augmenting path
        parent: dict[Any, Any | None] = {source: None}
        queue = deque([source])

        while queue and sink not in parent:
            u = queue.popleft()
            for v in adj[u]:
                if v not in parent and cap[u].get(v, 0.0) > 0:
                    parent[v] = u
                    queue.append(v)

        if sink not in parent:
            break  # No augmenting path found

        # Find bottleneck capacity along the path
        path_flow = float("inf")
        v = sink
        while parent[v] is not None:
            u = parent[v]
            path_flow = min(path_flow, cap[u].get(v, 0.0))
            v = u

        # Augment flow along the path
        v = sink
        while parent[v] is not None:
            u = parent[v]
            cap[u][v] = cap[u].get(v, 0.0) - path_flow
            cap[v][u] = cap[v].get(u, 0.0) + path_flow
            v = u

        flow_value += path_flow
        num_aug += 1

    # Build flow dictionary
    flow_dict: dict[Any, dict[Any, float]] = {}
    for u in graph.nodes():
        flow_dict[u] = {}
    for u in graph.nodes():
        for v in adj[u]:
            if v in orig_cap.get(u, {}):
                f = orig_cap[u][v] - cap[u].get(v, 0.0)
                if f > 0:
                    flow_dict[u][v] = f

    return MaxFlowResult(
        flow_value=float(flow_value),
        flow_dict=flow_dict,
        algorithm="edmonds_karp",
        source=source,
        sink=sink,
        num_augmentations=num_aug,
        metadata={"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()},
    )


def dinic_maxflow(
    graph: nx.DiGraph,
    source: Any,
    sink: Any,
    capacity: str = "capacity",
) -> MaxFlowResult:
    """
    Dinic's algorithm for maximum flow.

    Uses BFS to build a level graph, then DFS to find blocking flows.
    Achieves O(V² · E) time complexity, much faster than Edmonds-Karp
    on dense graphs.

    Parameters
    ----------
    graph : nx.DiGraph
        Input directed graph with edge capacities.
    source : node
        Source node.
    sink : node
        Sink node.
    capacity : str
        Edge attribute to use as capacity.

    Returns
    -------
    MaxFlowResult
        The maximum flow value and flow assignment.
    """
    if source not in graph or sink not in graph:
        raise ValueError("Source or sink not in graph")
    if source == sink:
        raise ValueError("Source and sink must be different")

    cap, adj, orig_cap = _build_capacity_graph(graph, capacity, source, sink)

    flow_value = 0.0
    num_aug = 0

    while True:
        # BFS: build level graph
        level: dict[Any, int] = {source: 0}
        queue = deque([source])

        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if v not in level and cap[u].get(v, 0.0) > 0:
                    level[v] = level[u] + 1
                    queue.append(v)

        if sink not in level:
            break  # No augmenting path

        # DFS: find blocking flow using level graph
        ptr: dict[Any, int] = {u: 0 for u in adj}  # current edge pointer

        def dfs(u: Any, pushed: float) -> float:
            if u == sink:
                return pushed
            neighbors = list(adj[u])
            while ptr[u] < len(neighbors):
                v = neighbors[ptr[u]]
                if cap[u].get(v, 0.0) > 0 and level.get(v, -1) == level[u] + 1:
                    tr = dfs(v, min(pushed, cap[u][v]))
                    if tr > 0:
                        cap[u][v] -= tr
                        cap[v][u] = cap[v].get(u, 0.0) + tr
                        return tr
                ptr[u] += 1
            return 0.0

        while True:
            pushed = dfs(source, float("inf"))
            if pushed == 0:
                break
            flow_value += pushed
            num_aug += 1

    # Build flow dictionary
    flow_dict: dict[Any, dict[Any, float]] = {}
    for u in graph.nodes():
        flow_dict[u] = {}
    for u in graph.nodes():
        for v in adj[u]:
            if v in orig_cap.get(u, {}):
                f = orig_cap[u][v] - cap[u].get(v, 0.0)
                if f > 0:
                    flow_dict[u][v] = f

    return MaxFlowResult(
        flow_value=float(flow_value),
        flow_dict=flow_dict,
        algorithm="dinic",
        source=source,
        sink=sink,
        num_augmentations=num_aug,
        metadata={"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()},
    )


def min_cut(
    graph: nx.DiGraph,
    source: Any,
    sink: Any,
    capacity: str = "capacity",
    algorithm: str = "dinic",
) -> MinCutResult:
    """
    Compute the minimum s-t cut using max-flow min-cut theorem.

    After computing max flow, the min cut is the set of edges from
    reachable nodes (in residual graph) to non-reachable nodes.

    Parameters
    ----------
    graph : nx.DiGraph
        Input directed graph with edge capacities.
    source : node
        Source node.
    sink : node
        Sink node.
    capacity : str
        Edge attribute to use as capacity.
    algorithm : str
        Max flow algorithm to use ("dinic" or "edmonds_karp").

    Returns
    -------
    MinCutResult
        The min cut value, partitions, and cut edges.
    """
    if algorithm == "dinic":
        mf = dinic_maxflow(graph, source, sink, capacity)
    elif algorithm == "edmonds_karp":
        mf = edmonds_karp(graph, source, sink, capacity)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    # Rebuild residual graph to find reachable nodes
    cap, adj, orig_cap = _build_capacity_graph(graph, capacity, source, sink)

    # Re-run to get final residual capacities
    # (We need the residual graph after max flow)
    # Reconstruct from flow_dict
    residual_cap: dict[Any, dict[Any, float]] = {}
    for u in graph.nodes():
        residual_cap[u] = {}
    for u in graph.nodes():
        for v in adj[u]:
            if v in orig_cap.get(u, {}):
                residual_cap[u][v] = orig_cap[u][v] - mf.flow_dict.get(u, {}).get(v, 0.0)
            else:
                residual_cap[u][v] = mf.flow_dict.get(v, {}).get(u, 0.0)

    # BFS from source in residual graph
    reachable: set = {source}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if v not in reachable and residual_cap[u].get(v, 0.0) > 0:
                reachable.add(v)
                queue.append(v)

    # Non-reachable = sink side
    non_reachable = set(graph.nodes()) - reachable

    # Cut edges: original edges from reachable to non-reachable
    cut_edges: list[tuple] = []
    cut_value = 0.0
    for u in reachable:
        for v in non_reachable:
            if v in orig_cap.get(u, {}):
                cut_edges.append((u, v))
                cut_value += orig_cap[u][v]

    return MinCutResult(
        cut_value=float(cut_value),
        partition_source=reachable,
        partition_sink=non_reachable,
        cut_edges=cut_edges,
        algorithm=algorithm,
        metadata={"max_flow": mf.flow_value, "num_cut_edges": len(cut_edges)},
    )


def flow_decomposition(
    flow_dict: dict,
    source: Any,
    sink: Any,
) -> list[dict]:
    """
    Decompose a flow into path flows and cycles.

    Parameters
    ----------
    flow_dict : dict
        Flow assignment from MaxFlowResult.
    source : node
        Source node.
    sink : node
        Sink node.

    Returns
    -------
    list of dict
        Each dict has keys: "path" (list of nodes), "flow" (float).
    """
    # Build residual flow network
    residual: dict[Any, dict[Any, float]] = {}
    for u in flow_dict:
        residual[u] = {}
        for v, f in flow_dict[u].items():
            if f > 0:
                residual[u][v] = f

    paths: list[dict] = []

    # Extract s-t paths
    while True:
        # BFS/DFS for a path from source to sink with positive flow
        parent: dict[Any, Any | None] = {source: None}
        stack = [source]
        found = False

        while stack and not found:
            u = stack.pop()
            for v in residual.get(u, {}):
                if v not in parent and residual[u][v] > 0:
                    parent[v] = u
                    if v == sink:
                        found = True
                        break
                    stack.append(v)

        if not found:
            break

        # Find bottleneck
        path_flow = float("inf")
        v = sink
        path = [sink]
        while parent[v] is not None:
            u = parent[v]
            path_flow = min(path_flow, residual[u][v])
            v = u
            path.append(v)
        path.reverse()

        # Subtract flow
        v = sink
        while parent[v] is not None:
            u = parent[v]
            residual[u][v] -= path_flow
            if residual[u][v] <= 0:
                del residual[u][v]
            v = u

        paths.append({"path": path, "flow": path_flow})

    # Extract cycles (flow remaining after path extraction)
    # Simple cycle detection via DFS
    visited: set = set()
    for start in list(residual.keys()):
        if start in visited:
            continue
        # Try to find a cycle from start
        path: list = []
        path_set: set = set()
        current = start

        while current not in path_set and current in residual and residual[current]:
            path.append(current)
            path_set.add(current)
            next_node = next(iter(residual[current]))
            if residual[current][next_node] <= 0:
                del residual[current][next_node]
                if not residual[current]:
                    del residual[current]
                break
            current = next_node

        if current in path_set:
            # Found a cycle
            cycle_start = path.index(current)
            cycle = path[cycle_start:] + [current]
            cycle_flow = float("inf")
            for i in range(len(cycle) - 1):
                cycle_flow = min(cycle_flow, residual[cycle[i]][cycle[i + 1]])
            for i in range(len(cycle) - 1):
                u, v = cycle[i], cycle[i + 1]
                residual[u][v] -= cycle_flow
                if residual[u][v] <= 0:
                    del residual[u][v]
            paths.append({"path": cycle, "flow": cycle_flow, "is_cycle": True})

        visited.update(path_set)

    return paths


def multi_source_multi_sink_flow(
    graph: nx.DiGraph,
    sources: list,
    sinks: list,
    capacity: str = "capacity",
    algorithm: str = "dinic",
) -> MaxFlowResult:
    """
    Max flow with multiple sources and sinks via super-source/super-sink.

    Adds a super-source connected to all sources with infinite capacity,
    and a super-sink connected from all sinks with infinite capacity.

    Parameters
    ----------
    graph : nx.DiGraph
        Input directed graph.
    sources : list
        List of source nodes.
    sinks : list
        List of sink nodes.
    capacity : str
        Edge attribute for capacity.
    algorithm : str
        Max flow algorithm.

    Returns
    -------
    MaxFlowResult
        Max flow from super-source to super-sink.
    """
    # Create augmented graph
    aug_graph = graph.copy()
    super_source = "__super_source__"
    super_sink = "__super_sink__"

    aug_graph.add_node(super_source)
    aug_graph.add_node(super_sink)

    for s in sources:
        aug_graph.add_edge(super_source, s, **{capacity: float("inf")})
    for t in sinks:
        aug_graph.add_edge(t, super_sink, **{capacity: float("inf")})

    if algorithm == "dinic":
        result = dinic_maxflow(aug_graph, super_source, super_sink, capacity)
    elif algorithm == "edmonds_karp":
        result = edmonds_karp(aug_graph, super_source, super_sink, capacity)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    # Remove super nodes from flow_dict
    flow_dict = {u: v_dict for u, v_dict in result.flow_dict.items()
                 if u not in (super_source, super_sink)}
    for u in flow_dict:
        flow_dict[u] = {v: f for v, f in flow_dict[u].items()
                        if v not in (super_source, super_sink)}

    result.flow_dict = flow_dict
    result.source = sources
    result.sink = sinks
    return result
