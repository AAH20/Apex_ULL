"""
Balanced Partitioning with Capacity Constraints
================================================

Problem Definition
------------------
Given an undirected graph G = (V, E) with edge weights w: E -> R+ and
node weights (capacities) c: V -> R+, partition V into k disjoint subsets
V₁, ..., Vₖ such that:

    cut(V₁, ..., Vₖ) = sum_{i<j} cut(Vᵢ, Vⱼ)

is minimized, subject to:

    sum_{v in Vᵢ} c(v) ≤ Cᵢ  for all i

where Cᵢ are per-partition capacity constraints. When all Cᵢ are equal,
this is the **balanced partitioning problem**; when they differ, it is
the **capacitated partitioning problem**.

Both variants are NP-hard. The balanced case with k=2 is the minimum
bisection problem.

Approximation Ratios
--------------------
- **Greedy balanced partition**: O(log n) approximation
- **LP relaxation + rounding**: O(√n) for general graphs
- **Local search (KL-style)**: No guarantee, but excellent in practice

Latency Impact
--------------
- Capacity constraints model real server memory/CPU limits
- Balanced partitions prevent hot-spotting on overloaded servers
- Critical for co-located trading systems where each server handles
  a subset of instruments
- Imbalanced partitions cause tail latency spikes (p99 degradation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import networkx as nx

from .bisection import kernighan_lin, spectral_bisection, BisectionResult


@dataclass
class BalancedPartitionResult:
    """Result of a balanced partition."""
    partitions: list[set]
    cut_weight: float
    partition_loads: list[float]
    algorithm: str
    iterations: int = 0
    metadata: dict = field(default_factory=dict)


def balanced_partition(
    graph: nx.Graph,
    k: int,
    node_weight: str = "weight",
    edge_weight: str = "weight",
    capacity: float | list[float] | None = None,
    balance_tolerance: float = 0.1,
    max_iterations: int = 100,
) -> BalancedPartitionResult:
    """
    Balanced partitioning with capacity constraints.

    Uses a two-phase approach:
    1. Initial partition via recursive spectral bisection
    2. Local search refinement that respects capacity constraints

    Time complexity: O(k · n² log n) for the refinement phase.

    Parameters
    ----------
    graph : nx.Graph
        Input graph.
    k : int
        Number of partitions.
    node_weight : str
        Node attribute for capacity/weight.
    edge_weight : str
        Edge attribute for edge weights.
    capacity : float or list of float, optional
        Per-partition capacity. If None, uses total_node_weight / k.
        If a single float, applies to all partitions.
    balance_tolerance : float
        Allowed deviation from perfect balance (0.1 = ±10%).
    max_iterations : int
        Maximum refinement iterations.

    Returns
    -------
    BalancedPartitionResult
        The balanced partition with load information.
    """
    if k < 2:
        raise ValueError("k must be >= 2")
    if k > len(graph):
        raise ValueError("k cannot exceed number of nodes")

    nodes = list(graph.nodes())
    n = len(nodes)

    # Compute node weights
    node_weights = {}
    for node in nodes:
        w = graph.nodes[node].get(node_weight, 1.0)
        node_weights[node] = w

    total_weight = sum(node_weights.values())

    # Set up capacity constraints
    if capacity is None:
        capacities = [total_weight / k] * k
    elif isinstance(capacity, (int, float)):
        capacities = [float(capacity)] * k
    else:
        capacities = list(capacity)
        if len(capacities) != k:
            raise ValueError(f"capacity list must have length {k}")

    # Phase 1: Initial partition via recursive bisection
    partitions = _initial_partition(graph, k, edge_weight)

    # Phase 2: Refinement with capacity constraints
    total_iterations = 0
    for iteration in range(max_iterations):
        improved = False

        # Compute current loads
        loads = [sum(node_weights[v] for v in part) for part in partitions]

        # Try moving nodes from overloaded to underloaded partitions
        for i in range(k):
            if loads[i] <= capacities[i] * (1 + balance_tolerance):
                continue

            # Find nodes to move from partition i
            candidates = list(partitions[i])
            # Sort by edge weight to other partitions (descending)
            candidates.sort(
                key=lambda v: sum(
                    data.get(edge_weight, 1.0)
                    for _, _, data in graph.edges(v, data=True)
                    if _ in partitions[i]
                ),
                reverse=True,
            )

            for node in candidates:
                if loads[i] <= capacities[i] * (1 + balance_tolerance):
                    break

                # Find best partition to move to
                best_target = -1
                best_cost = float("inf")

                for j in range(k):
                    if j == i:
                        continue
                    if loads[j] + node_weights[node] > capacities[j] * (1 + balance_tolerance):
                        continue

                    # Cost = increase in cut weight
                    cost = sum(
                        data.get(edge_weight, 1.0)
                        for _, neighbor, data in graph.edges(node, data=True)
                        if neighbor in partitions[j]
                    ) - sum(
                        data.get(edge_weight, 1.0)
                        for _, neighbor, data in graph.edges(node, data=True)
                        if neighbor in partitions[i] and neighbor != node
                    )

                    if cost < best_cost:
                        best_cost = cost
                        best_target = j

                if best_target >= 0:
                    partitions[i].remove(node)
                    partitions[best_target].add(node)
                    loads[i] -= node_weights[node]
                    loads[best_target] += node_weights[node]
                    improved = True
                    total_iterations += 1

        if not improved:
            break

    # Compute final cut weight
    cut_weight = 0.0
    for u, v, data in graph.edges(data=True):
        w = data.get(edge_weight, 1.0)
        u_part = None
        v_part = None
        for i, part in enumerate(partitions):
            if u in part:
                u_part = i
            if v in part:
                v_part = i
        if u_part is not None and v_part is not None and u_part != v_part:
            cut_weight += w

    return BalancedPartitionResult(
        partitions=partitions,
        cut_weight=float(cut_weight),
        partition_loads=loads,
        algorithm="balanced_partition",
        iterations=total_iterations,
        metadata={
            "k": k,
            "capacities": capacities,
            "balance_tolerance": balance_tolerance,
            "max_load_ratio": max(loads) / min(loads) if min(loads) > 0 else float("inf"),
        },
    )


def _initial_partition(graph: nx.Graph, k: int, weight: str) -> list[set]:
    """Create initial partition via recursive spectral bisection."""
    nodes = list(graph.nodes())

    def _bisect(subgraph: nx.Graph, remaining_k: int) -> list[set]:
        if remaining_k == 1:
            return [set(subgraph.nodes())]

        bisect_result = spectral_bisection(subgraph, weight=weight)

        left_subgraph = subgraph.subgraph(bisect_result.partition_a)
        right_subgraph = subgraph.subgraph(bisect_result.partition_b)

        left_k = remaining_k // 2
        right_k = remaining_k - left_k

        result = []
        if len(left_subgraph) > 0:
            result.extend(_bisect(left_subgraph, left_k))
        if len(right_subgraph) > 0:
            result.extend(_bisect(right_subgraph, right_k))
        return result

    return _bisect(graph, k)
