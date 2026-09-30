"""
ULL Routing Optimization Kernel
================================

Network routing algorithms for ultra-low-latency infrastructure optimization.

Sub-modules:
    mst         – Minimum Spanning Tree (Kruskal, Prim)
    maxflow     – Maximum Flow (Edmonds-Karp, Dinic, Min-Cut)
"""

from .mst import (
    MSTResult,
    UnionFind,
    kruskal_mst,
    prim_mst,
    mst_to_graph,
    mst_diameter,
    mst_max_edge_latency,
)
from .maxflow import (
    MaxFlowResult,
    MinCutResult,
    edmonds_karp,
    dinic_maxflow,
    min_cut,
    flow_decomposition,
    multi_source_multi_sink_flow,
)

__all__ = [
    # MST
    "MSTResult",
    "UnionFind",
    "kruskal_mst",
    "prim_mst",
    "mst_to_graph",
    "mst_diameter",
    "mst_max_edge_latency",
    # MaxFlow
    "MaxFlowResult",
    "MinCutResult",
    "edmonds_karp",
    "dinic_maxflow",
    "min_cut",
    "flow_decomposition",
    "multi_source_multi_sink_flow",
]

__version__ = "0.1.0"
