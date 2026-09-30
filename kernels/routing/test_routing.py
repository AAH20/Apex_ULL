"""
Tests for ULL Routing Optimization Kernel
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import networkx as nx
from kernels.routing import (
    kruskal_mst,
    prim_mst,
    mst_to_graph,
    mst_diameter,
    mst_max_edge_latency,
    edmonds_karp,
    dinic_maxflow,
    min_cut,
    flow_decomposition,
    multi_source_multi_sink_flow,
)


def create_test_graph() -> nx.Graph:
    """Create a test graph with known MST."""
    G = nx.Graph()
    edges = [
        (0, 1, 4.0), (0, 2, 1.0), (1, 2, 2.0),
        (1, 3, 5.0), (2, 3, 8.0), (2, 4, 10.0),
        (3, 4, 2.0), (3, 5, 6.0), (4, 5, 3.0),
    ]
    G.add_weighted_edges_from(edges)
    return G


def create_flow_graph() -> nx.DiGraph:
    """Create a test directed graph with capacities."""
    G = nx.DiGraph()
    edges = [
        ("s", "a", 10.0), ("s", "b", 5.0),
        ("a", "b", 15.0), ("a", "t", 10.0),
        ("b", "t", 10.0),
    ]
    G.add_weighted_edges_from(edges, weight="capacity")
    return G


def test_kruskal_basic():
    print("=== Testing Kruskal MST (Basic) ===")
    G = create_test_graph()
    result = kruskal_mst(G)
    print(f"  Total weight: {result.total_weight}")
    print(f"  Edges: {result.edges}")
    print(f"  Num edges: {result.num_edges}")
    assert result.num_edges == 5, f"Expected 5 edges, got {result.num_edges}"
    assert result.total_weight == 13.0, f"Expected 13.0, got {result.total_weight}"
    print("  ✓ PASSED\n")


def test_prim_basic():
    print("=== Testing Prim MST (Basic) ===")
    G = create_test_graph()
    result = prim_mst(G)
    print(f"  Total weight: {result.total_weight}")
    print(f"  Edges: {result.edges}")
    print(f"  Num edges: {result.num_edges}")
    assert result.num_edges == 5, f"Expected 5 edges, got {result.num_edges}"
    assert result.total_weight == 13.0, f"Expected 13.0, got {result.total_weight}"
    print("  ✓ PASSED\n")


def test_mst_algorithms_agree():
    print("=== Testing MST Algorithm Agreement ===")
    G = create_test_graph()
    kruskal = kruskal_mst(G)
    prim = prim_mst(G)
    print(f"  Kruskal weight: {kruskal.total_weight}")
    print(f"  Prim weight: {prim.total_weight}")
    assert abs(kruskal.total_weight - prim.total_weight) < 1e-9, \
        f"MST weights differ: {kruskal.total_weight} vs {prim.total_weight}"
    print("  ✓ PASSED\n")


def test_mst_to_graph():
    print("=== Testing MST to Graph Conversion ===")
    G = create_test_graph()
    result = kruskal_mst(G)
    mst_g = mst_to_graph(G, result)
    print(f"  MST nodes: {mst_g.number_of_nodes()}")
    print(f"  MST edges: {mst_g.number_of_edges()}")
    assert mst_g.number_of_nodes() == G.number_of_nodes()
    assert mst_g.number_of_edges() == result.num_edges
    assert nx.is_tree(mst_g), "MST graph should be a tree"
    print("  ✓ PASSED\n")


def test_mst_diameter():
    print("=== Testing MST Diameter ===")
    G = create_test_graph()
    result = kruskal_mst(G)
    mst_g = mst_to_graph(G, result)
    diam = mst_diameter(mst_g)
    print(f"  Diameter: {diam}")
    assert diam >= 1, "Diameter should be at least 1"
    print("  ✓ PASSED\n")


def test_mst_max_edge_latency():
    print("=== Testing MST Max Edge Latency ===")
    G = nx.Graph()
    edges = [
        (0, 1, 1.0), (1, 2, 5.0), (2, 3, 2.0),
        (0, 3, 10.0), (0, 2, 3.0),
    ]
    G.add_weighted_edges_from(edges, weight="latency")
    result = kruskal_mst(G, weight="latency")
    mst_g = mst_to_graph(G, result)
    max_lat = mst_max_edge_latency(mst_g, latency_attr="latency")
    print(f"  Max edge latency: {max_lat}")
    assert max_lat <= 5.0, f"Expected max latency <= 5.0, got {max_lat}"
    print("  ✓ PASSED\n")


def test_kruskal_disconnected():
    print("=== Testing Kruskal on Disconnected Graph ===")
    G = nx.Graph()
    G.add_edge(0, 1, weight=1.0)
    G.add_edge(2, 3, weight=2.0)
    result = kruskal_mst(G)
    print(f"  Edges: {result.edges}")
    print(f"  Weight: {result.total_weight}")
    # Should produce a spanning forest
    assert result.num_edges == 2, f"Expected 2 edges, got {result.num_edges}"
    print("  ✓ PASSED\n")


def test_edmonds_karp_basic():
    print("=== Testing Edmonds-Karp (Basic) ===")
    G = create_flow_graph()
    result = edmonds_karp(G, "s", "t")
    print(f"  Flow value: {result.flow_value}")
    print(f"  Augmentations: {result.num_augmentations}")
    assert result.flow_value == 15.0, f"Expected 15.0, got {result.flow_value}"
    print("  ✓ PASSED\n")


def test_dinic_basic():
    print("=== Testing Dinic's (Basic) ===")
    G = create_flow_graph()
    result = dinic_maxflow(G, "s", "t")
    print(f"  Flow value: {result.flow_value}")
    print(f"  Augmentations: {result.num_augmentations}")
    assert result.flow_value == 15.0, f"Expected 15.0, got {result.flow_value}"
    print("  ✓ PASSED\n")


def test_maxflow_algorithms_agree():
    print("=== Testing MaxFlow Algorithm Agreement ===")
    G = create_flow_graph()
    ek = edmonds_karp(G, "s", "t")
    dinic = dinic_maxflow(G, "s", "t")
    print(f"  Edmonds-Karp: {ek.flow_value}")
    print(f"  Dinic: {dinic.flow_value}")
    assert abs(ek.flow_value - dinic.flow_value) < 1e-9, \
        f"MaxFlow values differ: {ek.flow_value} vs {dinic.flow_value}"
    print("  ✓ PASSED\n")


def test_min_cut():
    print("=== Testing Min Cut ===")
    G = create_flow_graph()
    result = min_cut(G, "s", "t")
    print(f"  Cut value: {result.cut_value}")
    print(f"  Source side: {result.partition_source}")
    print(f"  Sink side: {result.partition_sink}")
    print(f"  Cut edges: {result.cut_edges}")
    assert result.cut_value == 15.0, f"Expected 15.0, got {result.cut_value}"
    assert "s" in result.partition_source
    assert "t" in result.partition_sink
    print("  ✓ PASSED\n")


def test_flow_decomposition():
    print("=== Testing Flow Decomposition ===")
    G = create_flow_graph()
    result = dinic_maxflow(G, "s", "t")
    paths = flow_decomposition(result.flow_dict, "s", "t")
    print(f"  Number of paths: {len(paths)}")
    total_path_flow = sum(p["flow"] for p in paths if not p.get("is_cycle", False))
    print(f"  Total path flow: {total_path_flow}")
    assert abs(total_path_flow - result.flow_value) < 1e-9, \
        f"Path flow sum {total_path_flow} != max flow {result.flow_value}"
    for p in paths:
        print(f"    Path: {' -> '.join(map(str, p['path']))}, flow={p['flow']}")
    print("  ✓ PASSED\n")


def test_multi_source_multi_sink():
    print("=== Testing Multi-Source Multi-Sink Flow ===")
    G = nx.DiGraph()
    edges = [
        ("s1", "a", 10.0), ("s2", "a", 5.0),
        ("a", "b", 15.0),
        ("b", "t1", 8.0), ("b", "t2", 7.0),
    ]
    G.add_weighted_edges_from(edges, weight="capacity")
    result = multi_source_multi_sink_flow(G, ["s1", "s2"], ["t1", "t2"])
    print(f"  Flow value: {result.flow_value}")
    assert result.flow_value == 15.0, f"Expected 15.0, got {result.flow_value}"
    print("  ✓ PASSED\n")


def test_larger_flow_network():
    print("=== Testing Larger Flow Network ===")
    G = nx.DiGraph()
    # Create a more complex network
    edges = [
        ("s", "a", 16.0), ("s", "b", 13.0),
        ("a", "b", 10.0), ("a", "c", 12.0),
        ("b", "a", 4.0), ("b", "d", 14.0),
        ("c", "b", 9.0), ("c", "t", 20.0),
        ("d", "c", 7.0), ("d", "t", 4.0),
    ]
    G.add_weighted_edges_from(edges, weight="capacity")
    result = dinic_maxflow(G, "s", "t")
    print(f"  Flow value: {result.flow_value}")
    assert result.flow_value == 23.0, f"Expected 23.0, got {result.flow_value}"
    print("  ✓ PASSED\n")


def test_empty_graph():
    print("=== Testing Empty Graph ===")
    G = nx.Graph()
    result = kruskal_mst(G)
    assert result.total_weight == 0.0
    assert result.num_edges == 0
    print("  ✓ PASSED\n")


def test_single_node():
    print("=== Testing Single Node ===")
    G = nx.Graph()
    G.add_node(0)
    result = kruskal_mst(G)
    assert result.total_weight == 0.0
    assert result.num_edges == 0
    print("  ✓ PASSED\n")


def test_directed_graph_mst_error():
    print("=== Testing Directed Graph MST Error ===")
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0)
    try:
        kruskal_mst(G)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  Correctly raised: {e}")
    print("  ✓ PASSED\n")


def test_same_source_sink_error():
    print("=== Testing Same Source/Sink Error ===")
    G = create_flow_graph()
    try:
        dinic_maxflow(G, "s", "s")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  Correctly raised: {e}")
    print("  ✓ PASSED\n")


if __name__ == "__main__":
    test_kruskal_basic()
    test_prim_basic()
    test_mst_algorithms_agree()
    test_mst_to_graph()
    test_mst_diameter()
    test_mst_max_edge_latency()
    test_kruskal_disconnected()
    test_edmonds_karp_basic()
    test_dinic_basic()
    test_maxflow_algorithms_agree()
    test_min_cut()
    test_flow_decomposition()
    test_multi_source_multi_sink()
    test_larger_flow_network()
    test_empty_graph()
    test_single_node()
    test_directed_graph_mst_error()
    test_same_source_sink_error()
    print("=" * 50)
    print("All tests passed ✓")
