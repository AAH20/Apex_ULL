"""
Graph Bisection
===============

Problem Definition
------------------
Given an undirected graph G = (V, E) with edge weights w: E -> R+, find a
partition of V into two disjoint subsets A and B such that:

    cut(A, B) = sum_{u in A, v in B} w(u, v)

is minimized, subject to a balance constraint |A| ≈ |B| (typically within
a tolerance ε, e.g., |A|/|B| ∈ [1-ε, 1+ε]).

This is the **minimum bisection problem**, which is NP-hard. All practical
algorithms are heuristics or approximation algorithms.

Algorithms
----------
1. **Kernighan-Lin (KL)** – O(n² log n) per pass, iterative improvement
   via node-pair swaps. Classic heuristic with no approximation guarantee
   but excellent practical results.

2. **Spectral Bisection** – O(n³) worst case (eigenvalue computation),
   uses the Fiedler vector (2nd smallest eigenvector of the Laplacian).
   Approximation ratio: O(√n) in the worst case, but typically much better
   on real-world graphs.

Latency Impact
--------------
In ULL systems, bisection minimizes cross-partition communication:
- Each cut edge represents a network hop (~1-5 μs with kernel bypass)
- Reducing cut weight directly reduces inter-server traffic
- Balanced partitions ensure no single server becomes a bottleneck
- Typical improvement: 30-50% reduction in cross-rack traffic vs random
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import networkx as nx
from scipy import sparse
from scipy.sparse.linalg import eigsh


@dataclass
class BisectionResult:
    """Result of a graph bisection."""
    partition_a: set
    partition_b: set
    cut_weight: float
    algorithm: str
    iterations: int = 0
    metadata: dict = field(default_factory=dict)


def kernighan_lin(
    graph: nx.Graph,
    initial_partition: tuple[set, set] | None = None,
    max_passes: int = 100,
    weight: str = "weight",
) -> BisectionResult:
    """
    Kernighan-Lin heuristic for graph bisection.

    Iteratively improves a partition by finding pairs of nodes (one from
    each side) whose swap reduces the cut weight the most. Each pass
    performs the best sequence of swaps found.

    Time complexity: O(n² log n) per pass.
    Space complexity: O(n²).

    Parameters
    ----------
    graph : nx.Graph
        Input graph with edge weights.
    initial_partition : tuple of two sets, optional
        Starting partition. If None, a random balanced split is used.
    max_passes : int
        Maximum number of improvement passes.
    weight : str
        Edge attribute to use as weight.

    Returns
    -------
    BisectionResult
        The improved partition and its cut weight.
    """
    nodes = list(graph.nodes())
    n = len(nodes)
    if n < 2:
        return BisectionResult(
            partition_a=set(nodes[:1]),
            partition_b=set(nodes[1:]),
            cut_weight=0.0,
            algorithm="kernighan_lin",
        )

    # Initialize partition
    if initial_partition is None:
        rng = np.random.default_rng(42)
        perm = rng.permutation(n)
        half = n // 2
        partition_a = {nodes[i] for i in perm[:half]}
        partition_b = {nodes[i] for i in perm[half:]}
    else:
        partition_a = set(initial_partition[0])
        partition_b = set(initial_partition[1])

    node_to_idx = {node: i for i, node in enumerate(nodes)}

    # Build adjacency matrix for fast lookups
    adj = nx.to_numpy_array(graph, nodelist=nodes, weight=weight)

    def compute_cut() -> float:
        """Compute total cut weight."""
        idx_a = [node_to_idx[n] for n in partition_a]
        idx_b = [node_to_idx[n] for n in partition_b]
        return float(adj[np.ix_(idx_a, idx_b)].sum())

    def compute_d_values() -> tuple[np.ndarray, np.ndarray]:
        """
        Compute D values: D[u] = external_cost(u) - internal_cost(u)
        where external_cost is sum of weights to nodes in the other partition,
        and internal_cost is sum of weights to nodes in the same partition.
        """
        idx_a = np.array([node_to_idx[n] for n in partition_a])
        idx_b = np.array([node_to_idx[n] for n in partition_b])

        d_a = adj[np.ix_(idx_a, idx_b)].sum(axis=1) - adj[np.ix_(idx_a, idx_a)].sum(axis=1)
        d_b = adj[np.ix_(idx_b, idx_a)].sum(axis=1) - adj[np.ix_(idx_b, idx_b)].sum(axis=1)
        return d_a, d_b

    best_cut = compute_cut()
    best_a = set(partition_a)
    best_b = set(partition_b)
    total_iterations = 0

    for pass_num in range(max_passes):
        # Track which nodes have been swapped in this pass
        swapped_a: set[int] = set()
        swapped_b: set[int] = set()
        swap_gains: list[float] = []
        swap_pairs: list[tuple[int, int]] = []

        # Perform up to n/2 swaps
        for _ in range(n // 2):
            d_a, d_b = compute_d_values()

            # Mask already-swapped nodes
            idx_a_list = [node_to_idx[n] for n in partition_a]
            idx_b_list = [node_to_idx[n] for n in partition_b]

            d_a_masked = np.full(len(partition_a), -np.inf)
            d_b_masked = np.full(len(partition_b), -np.inf)

            for i, ni in enumerate(idx_a_list):
                if ni not in swapped_a:
                    d_a_masked[i] = d_a[i]
            for i, ni in enumerate(idx_b_list):
                if ni not in swapped_b:
                    d_b_masked[i] = d_b[i]

            # Find best swap pair
            best_gain = -np.inf
            best_i, best_j = -1, -1

            for i in range(len(idx_a_list)):
                if d_a_masked[i] == -np.inf:
                    continue
                for j in range(len(idx_b_list)):
                    if d_b_masked[j] == -np.inf:
                        continue
                    gain = d_a_masked[i] + d_b_masked[j] - 2 * adj[idx_a_list[i], idx_b_list[j]]
                    if gain > best_gain:
                        best_gain = gain
                        best_i, best_j = i, j

            if best_gain <= 0:
                break

            # Record the swap
            swap_gains.append(best_gain)
            swap_pairs.append((idx_a_list[best_i], idx_b_list[best_j]))
            swapped_a.add(idx_a_list[best_i])
            swapped_b.add(idx_b_list[best_j])

            # Update D values incrementally
            node_a = idx_a_list[best_i]
            node_b = idx_b_list[best_j]
            for k, nk in enumerate(idx_a_list):
                if nk not in swapped_a:
                    d_a[k] += 2 * adj[nk, node_a] - 2 * adj[nk, node_b]
            for k, nk in enumerate(idx_b_list):
                if nk not in swapped_b:
                    d_b[k] += 2 * adj[nk, node_b] - 2 * adj[nk, node_a]

        if not swap_pairs:
            break

        # Find the prefix of swaps with maximum cumulative gain
        cumulative = np.cumsum(swap_gains)
        best_k = int(np.argmax(cumulative)) + 1

        if cumulative[best_k - 1] <= 0:
            break

        # Apply the best prefix of swaps
        for k in range(best_k):
            node_a, node_b = swap_pairs[k]
            partition_a.discard(nodes[node_a])
            partition_a.add(nodes[node_b])
            partition_b.discard(nodes[node_b])
            partition_b.add(nodes[node_a])

        total_iterations += best_k

        current_cut = compute_cut()
        if current_cut < best_cut:
            best_cut = current_cut
            best_a = set(partition_a)
            best_b = set(partition_b)

    return BisectionResult(
        partition_a=best_a,
        partition_b=best_b,
        cut_weight=best_cut,
        algorithm="kernighan_lin",
        iterations=total_iterations,
        metadata={"passes": pass_num + 1},
    )


def spectral_bisection(
    graph: nx.Graph,
    weight: str = "weight",
) -> BisectionResult:
    """
    Spectral bisection using the Fiedler vector.

    Computes the 2nd smallest eigenvector of the graph Laplacian and
    partitions nodes by the sign of their eigenvector component.

    Time complexity: O(n³) worst case, O(n²) for sparse graphs with
    iterative eigenvalue solvers.

    Approximation ratio: O(√n) in the worst case (for general graphs),
    but typically finds near-optimal bisections on well-structured graphs.

    Parameters
    ----------
    graph : nx.Graph
        Input graph with edge weights.
    weight : str
        Edge attribute to use as weight.

    Returns
    -------
    BisectionResult
        The spectral partition and its cut weight.
    """
    nodes = list(graph.nodes())
    n = len(nodes)
    if n < 2:
        return BisectionResult(
            partition_a=set(nodes[:1]),
            partition_b=set(nodes[1:]),
            cut_weight=0.0,
            algorithm="spectral_bisection",
        )

    # Build Laplacian matrix
    L = nx.laplacian_matrix(graph, nodelist=nodes, weight=weight).astype(float)

    # Compute the two smallest eigenvalues and eigenvectors
    # For small graphs, use dense; for large, use sparse iterative
    if n <= 500:
        eigenvalues, eigenvectors = np.linalg.eigh(L.toarray())
        fiedler = eigenvectors[:, 1]
    else:
        eigenvalues, eigenvectors = eigsh(L, k=2, which="SM")
        fiedler = eigenvectors[:, 1]

    # Partition by median of Fiedler vector (ensures balance)
    median_val = np.median(fiedler)
    partition_a = set()
    partition_b = set()

    for i, node in enumerate(nodes):
        if fiedler[i] <= median_val:
            partition_a.add(node)
        else:
            partition_b.add(node)

    # Handle edge case: all nodes on one side
    if not partition_a or not partition_b:
        sorted_indices = np.argsort(fiedler)
        half = n // 2
        partition_a = {nodes[i] for i in sorted_indices[:half]}
        partition_b = {nodes[i] for i in sorted_indices[half:]}

    # Compute cut weight
    cut_weight = 0.0
    for u, v, data in graph.edges(data=True):
        w = data.get(weight, 1.0)
        if (u in partition_a and v in partition_b) or (u in partition_b and v in partition_a):
            cut_weight += w

    return BisectionResult(
        partition_a=partition_a,
        partition_b=partition_b,
        cut_weight=float(cut_weight),
        algorithm="spectral_bisection",
        iterations=1,
        metadata={
            "fiedler_value": float(eigenvalues[1]),
            "eigenvalue_gap": float(eigenvalues[1] - eigenvalues[0]),
        },
    )
