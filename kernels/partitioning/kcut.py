"""
K-Way Cut (Graph K-Cut)
========================

Problem Definition
------------------
Given an undirected graph G = (V, E) with edge weights w: E -> R+, and
an integer k ≥ 2, partition V into k disjoint subsets V₁, V₂, ..., Vₖ such
that:

    cut(V₁, ..., Vₖ) = sum_{i<j} cut(Vᵢ, Vⱼ)

is minimized, subject to balance constraints on partition sizes.

This is the **minimum k-cut problem**, which is NP-hard for any fixed k ≥ 2.
For k = 2 it reduces to the minimum bisection problem.

Approximation Ratios
--------------------
- **Greedy K-Cut**: (2 - 2/k)-approximation [Saran & Vazirani, 1995]
- **Recursive Bisection**: (2 - 2/k)-approximation in the worst case
- **Spectral K-Cut**: O(√n) worst case, but often near-optimal in practice

Latency Impact
--------------
- Each cut edge = one inter-partition network hop
- K-cut directly models multi-server deployment topologies
- Minimizing k-cut reduces total cross-server communication volume
- Critical for distributed matching engines and order routing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import networkx as nx
from scipy import sparse
from scipy.sparse.linalg import eigsh

from .bisection import kernighan_lin, spectral_bisection, BisectionResult


@dataclass
class KCutResult:
    """Result of a k-way graph cut."""
    partitions: list[set]
    cut_weight: float
    algorithm: str
    iterations: int = 0
    metadata: dict = field(default_factory=dict)


def greedy_kcut(
    graph: nx.Graph,
    k: int,
    weight: str = "weight",
) -> KCutResult:
    """
    Greedy k-cut algorithm.

    Starts with all nodes in one partition and iteratively splits the
    partition whose division most reduces the cut weight, using spectral
    bisection for each split.

    Approximation ratio: (2 - 2/k) [Saran & Vazirani, 1995].

    Time complexity: O(k · T_bisect) where T_bisect is the cost of one
    bisection call.

    Parameters
    ----------
    graph : nx.Graph
        Input graph with edge weights.
    k : int
        Number of partitions (k ≥ 2).
    weight : str
        Edge attribute to use as weight.

    Returns
    -------
    KCutResult
        The k-way partition and its total cut weight.
    """
    if k < 2:
        raise ValueError("k must be >= 2")
    if k > len(graph):
        raise ValueError("k cannot exceed number of nodes")

    nodes = list(graph.nodes())

    # Start with one partition containing all nodes
    partitions: list[set] = [set(nodes)]
    total_iterations = 0

    while len(partitions) < k:
        # Find the partition to split (largest by total internal weight)
        best_idx = -1
        best_internal_weight = -1.0

        for i, part in enumerate(partitions):
            if len(part) < 2:
                continue
            subgraph = graph.subgraph(part)
            internal_weight = sum(
                data.get(weight, 1.0) for _, _, data in subgraph.edges(data=True)
            )
            if internal_weight > best_internal_weight:
                best_internal_weight = internal_weight
                best_idx = i

        if best_idx == -1:
            # All partitions are singletons; split arbitrarily
            for i, part in enumerate(partitions):
                if len(part) >= 2:
                    best_idx = i
                    break

        if best_idx == -1:
            break

        # Split the chosen partition using spectral bisection
        subgraph = graph.subgraph(partitions[best_idx])
        bisect_result = spectral_bisection(subgraph, weight=weight)
        total_iterations += bisect_result.iterations

        # Replace the partition with its two halves
        old_part = partitions.pop(best_idx)
        partitions.append(bisect_result.partition_a)
        partitions.append(bisect_result.partition_b)

    # Compute total cut weight
    cut_weight = 0.0
    for u, v, data in graph.edges(data=True):
        w = data.get(weight, 1.0)
        u_part = None
        v_part = None
        for i, part in enumerate(partitions):
            if u in part:
                u_part = i
            if v in part:
                v_part = i
        if u_part is not None and v_part is not None and u_part != v_part:
            cut_weight += w

    return KCutResult(
        partitions=partitions,
        cut_weight=float(cut_weight),
        algorithm="greedy_kcut",
        iterations=total_iterations,
        metadata={"k": k, "num_partitions": len(partitions)},
    )


def recursive_bisection(
    graph: nx.Graph,
    k: int,
    weight: str = "weight",
    refine: bool = True,
) -> KCutResult:
    """
    Recursive bisection for k-way partitioning.

    Recursively bisects the graph k-1 times to produce k partitions.
    Optionally refines the result with Kernighan-Lin passes.

    Approximation ratio: (2 - 2/k) in the worst case.

    Time complexity: O(k · n² log n) with KL refinement.

    Parameters
    ----------
    graph : nx.Graph
        Input graph with edge weights.
    k : int
        Number of partitions (k ≥ 2).
    weight : str
        Edge attribute to use as weight.
    refine : bool
        If True, apply Kernighan-Lin refinement after initial partitioning.

    Returns
    -------
    KCutResult
        The k-way partition and its total cut weight.
    """
    if k < 2:
        raise ValueError("k must be >= 2")
    if k > len(graph):
        raise ValueError("k cannot exceed number of nodes")

    nodes = list(graph.nodes())

    # Recursive bisection
    def _recursive_bisect(subgraph: nx.Graph, remaining_k: int) -> list[set]:
        if remaining_k == 1:
            return [set(subgraph.nodes())]

        # Bisect the subgraph
        bisect_result = spectral_bisection(subgraph, weight=weight)

        # Recursively bisect each half
        left_subgraph = subgraph.subgraph(bisect_result.partition_a)
        right_subgraph = subgraph.subgraph(bisect_result.partition_b)

        left_k = remaining_k // 2
        right_k = remaining_k - left_k

        result = []
        if len(left_subgraph) > 0:
            result.extend(_recursive_bisect(left_subgraph, left_k))
        if len(right_subgraph) > 0:
            result.extend(_recursive_bisect(right_subgraph, right_k))
        return result

    partitions = _recursive_bisect(graph, k)

    # Refine with Kernighan-Lin if requested
    total_iterations = 0
    if refine and len(partitions) == 2:
        bisect_result = kernighan_lin(graph, (partitions[0], partitions[1]), weight=weight)
        total_iterations += bisect_result.iterations
        partitions = [bisect_result.partition_a, bisect_result.partition_b]

    # Compute total cut weight
    cut_weight = 0.0
    for u, v, data in graph.edges(data=True):
        w = data.get(weight, 1.0)
        u_part = None
        v_part = None
        for i, part in enumerate(partitions):
            if u in part:
                u_part = i
            if v in part:
                v_part = i
        if u_part is not None and v_part is not None and u_part != v_part:
            cut_weight += w

    return KCutResult(
        partitions=partitions,
        cut_weight=float(cut_weight),
        algorithm="recursive_bisection",
        iterations=total_iterations,
        metadata={"k": k, "refined": refine, "num_partitions": len(partitions)},
    )
