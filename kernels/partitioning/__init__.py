"""
ULL Partitioning Optimization Kernel
=====================================

Graph partitioning algorithms for ultra-low-latency infrastructure optimization.

Sub-modules:
    bisection   – Graph bisection (2-way partition)
    kcut        – K-way cut (generalization to k partitions)
    balanced    – Balanced partitioning with capacity constraints
    community   – Community detection (modularity-based)
    latency     – Latency impact model for partition quality
"""

from .bisection import kernighan_lin, spectral_bisection, BisectionResult
from .kcut import greedy_kcut, recursive_bisection, KCutResult
from .balanced import balanced_partition, BalancedPartitionResult
from .community import louvain_communities, label_propagation, CommunityResult
from .latency import LatencyModel, estimate_partition_latency, compare_partitions

__all__ = [
    "kernighan_lin",
    "spectral_bisection",
    "BisectionResult",
    "greedy_kcut",
    "recursive_bisection",
    "KCutResult",
    "balanced_partition",
    "BalancedPartitionResult",
    "louvain_communities",
    "label_propagation",
    "CommunityResult",
    "LatencyModel",
    "estimate_partition_latency",
    "compare_partitions",
]

__version__ = "0.1.0"
