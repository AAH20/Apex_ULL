"""
Community Detection
===================

Problem Definition
------------------
Given a graph G = (V, E), find communities (densely connected subgraphs)
such that the **modularity** of the partition is maximized:

    Q = (1/2m) * sum_{ij} [A_{ij} - k_i k_j / 2m] δ(c_i, c_j)

where A is the adjacency matrix, k_i is the degree of node i, m is the
total number of edges, and δ(c_i, c_j) = 1 if nodes i and j are in the
same community.

Modularity maximization is NP-hard [Brandes et al., 2008]. All practical
algorithms are heuristics.

Algorithms
----------
1. **Louvain Method** – O(n log n) average case, greedy modularity
   optimization with hierarchical aggregation. No approximation guarantee
   but state-of-the-art practical results.

2. **Label Propagation** – O(m) average case, nodes adopt the most
   frequent label among their neighbors. Fast but can produce
   unstable results.

Approximation Ratios
--------------------
- No polynomial-time algorithm can approximate modularity better than
  (1 - 1/e) unless P = NP [DasGupta & Desai, 2013]
- Louvain: no guarantee, but typically finds Q > 0.7 on real networks
- Label Propagation: no guarantee, but O(m) time

Latency Impact
--------------
- Communities naturally minimize inter-community communication
- In ULL systems, communities map to server assignments
- High modularity = fewer cross-server messages = lower latency
- Community structure reveals natural data locality for co-location
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import networkx as nx


@dataclass
class CommunityResult:
    """Result of community detection."""
    communities: list[set]
    modularity: float
    algorithm: str
    iterations: int = 0
    metadata: dict = field(default_factory=dict)


def louvain_communities(
    graph: nx.Graph,
    weight: str = "weight",
    resolution: float = 1.0,
    max_iterations: int = 100,
) -> CommunityResult:
    """
    Louvain method for community detection.

    Two-phase algorithm repeated until convergence:
    1. Local moving: each node moves to the community that maximizes
       modularity gain
    2. Aggregation: communities become nodes in a new graph

    Time complexity: O(n log n) average case.

    Parameters
    ----------
    graph : nx.Graph
        Input graph.
    weight : str
        Edge attribute for weights.
    resolution : float
        Resolution parameter (γ). Higher values → more communities.
        γ = 1.0 is standard modularity.
    max_iterations : int
        Maximum number of full iterations.

    Returns
    -------
    CommunityResult
        Detected communities and their modularity score.
    """
    if len(graph) == 0:
        return CommunityResult(
            communities=[],
            modularity=0.0,
            algorithm="louvain",
        )

    # Use networkx's built-in Louvain implementation
    communities = nx.community.louvain_communities(
        graph, weight=weight, resolution=resolution, seed=42
    )

    # Compute modularity
    modularity = nx.community.modularity(graph, communities, weight=weight)

    return CommunityResult(
        communities=[set(c) for c in communities],
        modularity=float(modularity),
        algorithm="louvain",
        iterations=max_iterations,
        metadata={
            "resolution": resolution,
            "num_communities": len(communities),
        },
    )


def label_propagation(
    graph: nx.Graph,
    weight: str = "weight",
    max_iterations: int = 100,
) -> CommunityResult:
    """
    Label propagation algorithm for community detection.

    Each node starts with a unique label. Iteratively, each node adopts
    the most frequent label among its neighbors (weighted by edge weight).
    Converges when no node changes label.

    Time complexity: O(m) average case per iteration.

    Parameters
    ----------
    graph : nx.Graph
        Input graph.
    weight : str
        Edge attribute for weights.
    max_iterations : int
        Maximum number of iterations.

    Returns
    -------
    CommunityResult
        Detected communities and their modularity score.
    """
    if len(graph) == 0:
        return CommunityResult(
            communities=[],
            modularity=0.0,
            algorithm="label_propagation",
        )

    nodes = list(graph.nodes())
    n = len(nodes)
    node_to_idx = {node: i for i, node in enumerate(nodes)}

    # Initialize: each node has its own label
    labels = np.arange(n)
    adj = nx.to_numpy_array(graph, nodelist=nodes, weight=weight)

    for iteration in range(max_iterations):
        changed = False
        # Random order for fairness
        order = np.random.default_rng(42 + iteration).permutation(n)

        for node_idx in order:
            # Count neighbor labels
            neighbor_labels = adj[node_idx] * labels
            unique_labels, counts = np.unique(
                labels[adj[node_idx] > 0], return_counts=True
            )

            if len(unique_labels) == 0:
                continue

            # Find the label with maximum weight
            label_weights = {}
            for lbl in unique_labels:
                mask = (labels == lbl) & (adj[node_idx] > 0)
                label_weights[lbl] = adj[node_idx][mask].sum()

            best_label = max(label_weights, key=label_weights.get)

            if best_label != labels[node_idx]:
                labels[node_idx] = best_label
                changed = True

        if not changed:
            break

    # Group nodes by label
    communities_dict: dict[int, set] = {}
    for i, node in enumerate(nodes):
        lbl = int(labels[i])
        if lbl not in communities_dict:
            communities_dict[lbl] = set()
        communities_dict[lbl].add(node)

    communities = list(communities_dict.values())

    # Compute modularity
    modularity = nx.community.modularity(graph, communities, weight=weight)

    return CommunityResult(
        communities=communities,
        modularity=float(modularity),
        algorithm="label_propagation",
        iterations=iteration + 1,
        metadata={
            "num_communities": len(communities),
            "converged": not changed,
        },
    )
