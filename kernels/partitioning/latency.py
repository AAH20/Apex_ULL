"""
Latency Impact Model for Graph Partitioning
============================================

Models the relationship between graph partition quality and end-to-end
system latency in ultra-low-latency infrastructure.

Key Insight
-----------
In distributed ULL systems, graph edges represent communication channels
between components (servers, processes, FPGA kernels). The partition
determines which components co-locate on the same physical server.

Latency Components
------------------
1. **Intra-partition latency**: Communication within a server
   - Shared memory: ~100 ns
   - PCIe: ~500 ns
   - Same FPGA: ~50 ns

2. **Inter-partition latency**: Communication across servers
   - Kernel bypass (DPDK/Onload): ~1-5 μs
   - Standard network stack: ~10-50 μs
   - Cross-rack: ~50-100 μs

3. **Queueing delay**: From imbalanced partitions
   - M/M/1 queue: E[T] = 1/(μ - λ)
   - Imbalanced load → λ > μ → unbounded queue growth

The total latency is dominated by inter-partition communication, making
partition quality critical for ULL systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import networkx as nx


@dataclass
class LatencyModel:
    """
    Latency model for partitioned systems.

    Parameters
    ----------
    intra_latency : float
        Latency for intra-partition communication (seconds).
    inter_latency : float
        Latency for inter-partition communication (seconds).
    queue_factor : float
        Multiplier for queueing delay from load imbalance.
    """

    intra_latency: float = 100e-9  # 100 ns
    inter_latency: float = 2e-6     # 2 μs
    queue_factor: float = 1.0

    def estimate_latency(
        self,
        graph: nx.Graph,
        partitions: list[set],
        edge_weight: str = "weight",
        node_weight: str = "weight",
    ) -> dict[str, float]:
        """
        Estimate latency components for a given partition.

        Returns
        -------
        dict with keys:
            - intra_latency: Total intra-partition latency
            - inter_latency: Total inter-partition latency
            - queue_latency: Estimated queueing delay
            - total_latency: Sum of all components
            - cut_weight: Total weight of cut edges
            - num_cut_edges: Number of edges crossing partitions
        """
        # Compute cut edges
        cut_weight = 0.0
        num_cut_edges = 0
        intra_weight = 0.0

        for u, v, data in graph.edges(data=True):
            w = data.get(edge_weight, 1.0)
            u_part = None
            v_part = None
            for i, part in enumerate(partitions):
                if u in part:
                    u_part = i
                if v in part:
                    v_part = i

            if u_part is not None and v_part is not None:
                if u_part != v_part:
                    cut_weight += w
                    num_cut_edges += 1
                else:
                    intra_weight += w

        # Compute load imbalance
        loads = []
        for part in partitions:
            load = sum(graph.nodes[v].get(node_weight, 1.0) for v in part)
            loads.append(load)

        max_load = max(loads) if loads else 1.0
        min_load = min(loads) if loads else 1.0
        avg_load = np.mean(loads) if loads else 1.0

        # Queueing delay model: proportional to (max_load / avg_load - 1)
        imbalance_ratio = max_load / avg_load if avg_load > 0 else 1.0
        queue_latency = self.queue_factor * (imbalance_ratio - 1.0) * self.inter_latency

        # Total latencies
        total_intra = intra_weight * self.intra_latency
        total_inter = cut_weight * self.inter_latency
        total = total_intra + total_inter + queue_latency

        return {
            "intra_latency": total_intra,
            "inter_latency": total_inter,
            "queue_latency": queue_latency,
            "total_latency": total,
            "cut_weight": cut_weight,
            "num_cut_edges": num_cut_edges,
            "imbalance_ratio": imbalance_ratio,
        }


def estimate_partition_latency(
    graph: nx.Graph,
    partitions: list[set],
    edge_weight: str = "weight",
    node_weight: str = "weight",
    intra_latency: float = 100e-9,
    inter_latency: float = 2e-6,
) -> dict[str, float]:
    """
    Convenience function to estimate latency for a partition.

    See LatencyModel.estimate_latency for details.
    """
    model = LatencyModel(
        intra_latency=intra_latency,
        inter_latency=inter_latency,
    )
    return model.estimate_latency(graph, partitions, edge_weight, node_weight)


def compare_partitions(
    graph: nx.Graph,
    partitions_list: list[list[set]],
    labels: list[str] | None = None,
    edge_weight: str = "weight",
    node_weight: str = "weight",
) -> dict[str, dict[str, float]]:
    """
    Compare multiple partitions by their latency characteristics.

    Returns
    -------
    dict mapping label → latency metrics
    """
    if labels is None:
        labels = [f"partition_{i}" for i in range(len(partitions_list))]

    model = LatencyModel()
    results = {}
    for label, partitions in zip(labels, partitions_list):
        results[label] = model.estimate_latency(
            graph, partitions, edge_weight, node_weight
        )
    return results
