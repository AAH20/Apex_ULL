"""
Tests for ULL Partitioning Optimization Kernel
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import networkx as nx
from kernels.partitioning import (
    kernighan_lin,
    spectral_bisection,
    greedy_kcut,
    recursive_bisection,
    balanced_partition,
    louvain_communities,
    label_propagation,
    LatencyModel,
    estimate_partition_latency,
    compare_partitions,
)


def create_test_graph() -> nx.Graph:
    """Create a test graph with known community structure."""
    # Two cliques of 5 nodes connected by a single edge
    G = nx.Graph()
    # Clique 1
    for i in range(5):
        for j in range(i + 1, 5):
            G.add_edge(i, j, weight=1.0)
    # Clique 2
    for i in range(5, 10):
        for j in range(i + 1, 10):
            G.add_edge(i, j, weight=1.0)
    # Bridge
    G.add_edge(2, 7, weight=0.5)
    return G


def create_weighted_test_graph() -> nx.Graph:
    """Create a weighted test graph."""
    G = nx.Graph()
    edges = [
        (0, 1, 5.0), (0, 2, 3.0), (1, 2, 4.0),
        (3, 4, 5.0), (3, 5, 3.0), (4, 5, 4.0),
        (2, 3, 1.0),  # Bridge
        (6, 7, 5.0), (6, 8, 3.0), (7, 8, 4.0),
        (5, 6, 1.0),  # Bridge
    ]
    G.add_weighted_edges_from(edges)
    return G


def test_kernighan_lin():
    print("=== Testing Kernighan-Lin ===")
    G = create_test_graph()
    result = kernighan_lin(G)
    print(f"  Cut weight: {result.cut_weight}")
    print(f"  Partition A: {sorted(result.partition_a)}")
    print(f"  Partition B: {sorted(result.partition_b)}")
    print(f"  Iterations: {result.iterations}")
    assert result.cut_weight <= 1.0, f"Expected cut <= 1.0, got {result.cut_weight}"
    assert len(result.partition_a) + len(result.partition_b) == len(G)
    print("  ✓ PASSED\n")


def test_spectral_bisection():
    print("=== Testing Spectral Bisection ===")
    G = create_test_graph()
    result = spectral_bisection(G)
    print(f"  Cut weight: {result.cut_weight}")
    print(f"  Partition A: {sorted(result.partition_a)}")
    print(f"  Partition B: {sorted(result.partition_b)}")
    print(f"  Fiedler value: {result.metadata.get('fiedler_value', 'N/A')}")
    assert result.cut_weight <= 1.0, f"Expected cut <= 1.0, got {result.cut_weight}"
    assert len(result.partition_a) + len(result.partition_b) == len(G)
    print("  ✓ PASSED\n")


def test_greedy_kcut():
    print("=== Testing Greedy K-Cut ===")
    G = create_weighted_test_graph()
    result = greedy_kcut(G, k=3)
    print(f"  Cut weight: {result.cut_weight}")
    print(f"  Number of partitions: {len(result.partitions)}")
    for i, part in enumerate(result.partitions):
        print(f"  Partition {i}: {sorted(part)}")
    assert len(result.partitions) == 3
    # All nodes should be assigned
    all_nodes = set()
    for part in result.partitions:
        all_nodes.update(part)
    assert all_nodes == set(G.nodes())
    print("  ✓ PASSED\n")


def test_recursive_bisection():
    print("=== Testing Recursive Bisection ===")
    G = create_weighted_test_graph()
    result = recursive_bisection(G, k=3, refine=True)
    print(f"  Cut weight: {result.cut_weight}")
    print(f"  Number of partitions: {len(result.partitions)}")
    for i, part in enumerate(result.partitions):
        print(f"  Partition {i}: {sorted(part)}")
    assert len(result.partitions) == 3
    all_nodes = set()
    for part in result.partitions:
        all_nodes.update(part)
    assert all_nodes == set(G.nodes())
    print("  ✓ PASSED\n")


def test_balanced_partition():
    print("=== Testing Balanced Partition ===")
    G = create_weighted_test_graph()
    # Add node weights
    for node in G.nodes():
        G.nodes[node]["weight"] = 1.0
    result = balanced_partition(G, k=3, node_weight="weight", edge_weight="weight")
    print(f"  Cut weight: {result.cut_weight}")
    print(f"  Partition loads: {result.partition_loads}")
    print(f"  Max load ratio: {result.metadata.get('max_load_ratio', 'N/A')}")
    for i, part in enumerate(result.partitions):
        print(f"  Partition {i}: {sorted(part)}")
    assert len(result.partitions) == 3
    print("  ✓ PASSED\n")


def test_louvain():
    print("=== Testing Louvain Community Detection ===")
    G = create_test_graph()
    result = louvain_communities(G)
    print(f"  Modularity: {result.modularity}")
    print(f"  Number of communities: {len(result.communities)}")
    for i, comm in enumerate(result.communities):
        print(f"  Community {i}: {sorted(comm)}")
    assert result.modularity > 0.3, f"Expected modularity > 0.3, got {result.modularity}"
    print("  ✓ PASSED\n")


def test_label_propagation():
    print("=== Testing Label Propagation ===")
    G = create_test_graph()
    result = label_propagation(G)
    print(f"  Modularity: {result.modularity}")
    print(f"  Number of communities: {len(result.communities)}")
    for i, comm in enumerate(result.communities):
        print(f"  Community {i}: {sorted(comm)}")
    assert result.modularity > 0.0, f"Expected modularity > 0, got {result.modularity}"
    print("  ✓ PASSED\n")


def test_latency_model():
    print("=== Testing Latency Model ===")
    G = create_test_graph()
    model = LatencyModel(intra_latency=100e-9, inter_latency=2e-6)

    # Good partition (respects community structure)
    good_partition = [{0, 1, 2, 3, 4}, {5, 6, 7, 8, 9}]
    good_metrics = model.estimate_latency(G, good_partition)
    print(f"  Good partition total latency: {good_metrics['total_latency']*1e6:.2f} μs")
    print(f"  Good partition cut weight: {good_metrics['cut_weight']}")

    # Bad partition (splits communities)
    bad_partition = [{0, 5}, {1, 6}, {2, 7}, {3, 8}, {4, 9}]
    bad_metrics = model.estimate_latency(G, bad_partition)
    print(f"  Bad partition total latency: {bad_metrics['total_latency']*1e6:.2f} μs")
    print(f"  Bad partition cut weight: {bad_metrics['cut_weight']}")

    assert good_metrics['cut_weight'] < bad_metrics['cut_weight']
    assert good_metrics['total_latency'] < bad_metrics['total_latency']
    print("  ✓ PASSED\n")


def test_compare_partitions():
    print("=== Testing Partition Comparison ===")
    G = create_test_graph()
    partitions = [
        [{0, 1, 2, 3, 4}, {5, 6, 7, 8, 9}],
        [{0, 5}, {1, 6}, {2, 7}, {3, 8}, {4, 9}],
    ]
    results = compare_partitions(G, partitions, labels=["good", "bad"])
    for label, metrics in results.items():
        print(f"  {label}: total_latency={metrics['total_latency']*1e6:.2f} μs, cut={metrics['cut_weight']}")
    assert results["good"]["cut_weight"] < results["bad"]["cut_weight"]
    print("  ✓ PASSED\n")


def test_large_graph():
    print("=== Testing on Larger Graph (100 nodes) ===")
    G = nx.barabasi_albert_graph(100, 3, seed=42)
    for u, v in G.edges():
        G[u][v]["weight"] = 1.0

    result = spectral_bisection(G)
    print(f"  Spectral bisection cut: {result.cut_weight}")
    print(f"  Partition sizes: {len(result.partition_a)}, {len(result.partition_b)}")

    result = kernighan_lin(G)
    print(f"  KL bisection cut: {result.cut_weight}")
    print(f"  Partition sizes: {len(result.partition_a)}, {len(result.partition_b)}")

    result = louvain_communities(G)
    print(f"  Louvain modularity: {result.modularity}")
    print(f"  Number of communities: {len(result.communities)}")
    print("  ✓ PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("ULL Partitioning Optimization Kernel - Test Suite")
    print("=" * 60 + "\n")

    test_kernighan_lin()
    test_spectral_bisection()
    test_greedy_kcut()
    test_recursive_bisection()
    test_balanced_partition()
    test_louvain()
    test_label_propagation()
    test_latency_model()
    test_compare_partitions()
    test_large_graph()

    print("=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
