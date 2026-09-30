"""
Tests for ULL Scheduling Optimization Kernel
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from kernels.scheduling import (
    JSSPSolver, JSSPInstance,
    FSSPSolver, FSSPInstance,
    OSSPSolver, OSSPInstance,
    RCPSPSolver, RCPSPInstance,
    BranchAndBound, DynamicProgramming, IntegerLinearProgramming,
    PTAS, FPTAS, RoundingScheme,
    GeneticAlgorithm, SimulatedAnnealing, AntColonyOptimization, ParticleSwarmOptimization,
    LargeNeighborhoodSearch, Matheuristic,
    GNNPredictor, RLPolicy, TransformerScheduler,
)


def create_test_jssp() -> JSSPInstance:
    """Create a small JSSP test instance (3 jobs, 3 machines)."""
    return JSSPInstance(
        n_jobs=3,
        n_machines=3,
        processing_times=[[3, 2, 2], [2, 3, 2], [2, 2, 3]],
        machine_sequence=[[0, 1, 2], [1, 0, 2], [0, 1, 2]],
    )


def create_test_fssp() -> FSSPInstance:
    """Create a small FSSP test instance (4 jobs, 3 machines)."""
    return FSSPInstance(
        n_jobs=4,
        n_machines=3,
        processing_times=[[3, 2, 4], [2, 3, 1], [4, 1, 3], [1, 4, 2]],
    )


def create_test_ossp() -> OSSPInstance:
    """Create a small OSSP test instance (3 jobs, 3 machines)."""
    return OSSPInstance(
        n_jobs=3,
        n_machines=3,
        processing_times=[[3, 2, 2], [2, 3, 2], [2, 2, 3]],
    )


def create_test_rcpsp() -> RCPSPInstance:
    """Create a small RCPSP test instance (4 activities, 1 resource)."""
    return RCPSPInstance(
        n_activities=4,
        n_resources=1,
        durations=[3, 2, 4, 1],
        resource_reqs=[[1], [1], [1], [1]],
        resource_capacities=[2],
        successors=[[1, 2], [3], [3], []],
        predecessors=[[], [0], [0], [1, 2]],
    )


def test_jssp():
    print("=== Testing JSSP ===")
    instance = create_test_jssp()
    solver = JSSPSolver()

    # Test GT
    sol = solver.solve(instance, algorithm="gt")
    print(f"  GT: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test local search
    sol = solver.solve(instance, algorithm="local", max_iterations=100)
    print(f"  Local: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test tabu search
    sol = solver.solve(instance, algorithm="tabu", max_iterations=100)
    print(f"  Tabu: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_fssp():
    print("=== Testing FSSP ===")
    instance = create_test_fssp()
    solver = FSSPSolver()

    # Test NEH
    sol = solver.solve(instance, algorithm="neh")
    print(f"  NEH: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test Palmer
    sol = solver.solve(instance, algorithm="palmer")
    print(f"  Palmer: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test CDS
    sol = solver.solve(instance, algorithm="cds")
    print(f"  CDS: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test SA
    sol = solver.solve(instance, algorithm="sa", max_iterations=100)
    print(f"  SA: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test GA
    sol = solver.solve(instance, algorithm="ga", max_iterations=50, population_size=20)
    print(f"  GA: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test LNS
    sol = solver.solve(instance, algorithm="lns", max_iterations=50)
    print(f"  LNS: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_ossp():
    print("=== Testing OSSP ===")
    instance = create_test_ossp()
    solver = OSSPSolver()

    # Test GT
    sol = solver.solve(instance, algorithm="gt")
    print(f"  GT: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test SA
    sol = solver.solve(instance, algorithm="sa", max_iterations=100)
    print(f"  SA: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test LNS
    sol = solver.solve(instance, algorithm="lns", max_iterations=50)
    print(f"  LNS: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_rcpsp():
    print("=== Testing RCPSP ===")
    instance = create_test_rcpsp()
    solver = RCPSPSolver()

    # Test serial SGS
    sol = solver.solve(instance, algorithm="serial_sgs")
    print(f"  Serial SGS: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test parallel SGS
    sol = solver.solve(instance, algorithm="parallel_sgs")
    print(f"  Parallel SGS: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test local search
    sol = solver.solve(instance, algorithm="local", max_iterations=50)
    print(f"  Local: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_exact():
    print("=== Testing Exact Solvers ===")
    jssp_instance = create_test_jssp()
    fssp_instance = create_test_fssp()

    # Test Branch and Bound
    bnb = BranchAndBound(time_limit_ms=100.0)
    sol = bnb.solve_jssp(
        jssp_instance.n_jobs,
        jssp_instance.n_machines,
        jssp_instance.processing_times,
        jssp_instance.machine_sequence,
    )
    print(f"  BnB JSSP: makespan={sol.makespan}, nodes={sol.nodes_explored}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test DP
    dp = DynamicProgramming(time_limit_ms=100.0)
    sol = dp.solve_jssp(
        jssp_instance.n_jobs,
        jssp_instance.n_machines,
        jssp_instance.processing_times,
        jssp_instance.machine_sequence,
    )
    print(f"  DP JSSP: makespan={sol.makespan}, nodes={sol.nodes_explored}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test ILP
    ilp = IntegerLinearProgramming(time_limit_ms=100.0)
    sol = ilp.solve_jssp(
        jssp_instance.n_jobs,
        jssp_instance.n_machines,
        jssp_instance.processing_times,
        jssp_instance.machine_sequence,
    )
    print(f"  ILP JSSP: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_approximation():
    print("=== Testing Approximation Algorithms ===")
    jssp_instance = create_test_jssp()
    fssp_instance = create_test_fssp()

    # Test PTAS
    ptas = PTAS(epsilon=0.1)
    sol = ptas.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
    )
    print(f"  PTAS FSSP: makespan={sol.makespan}, ratio={sol.approximation_ratio:.2f}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test FPTAS
    fptas = FPTAS(epsilon=0.1)
    sol = fptas.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
    )
    print(f"  FPTAS FSSP: makespan={sol.makespan}, ratio={sol.approximation_ratio:.2f}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test Rounding
    rounding = RoundingScheme(epsilon=0.1)
    sol = rounding.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
    )
    print(f"  Rounding FSSP: makespan={sol.makespan}, ratio={sol.approximation_ratio:.2f}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_metaheuristic():
    print("=== Testing Metaheuristic Solvers ===")
    fssp_instance = create_test_fssp()

    # Test GA
    ga = GeneticAlgorithm(population_size=20, seed=42)
    sol = ga.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
        max_iterations=50,
        time_limit_ms=100.0,
    )
    print(f"  GA FSSP: makespan={sol.makespan}, iters={sol.iterations}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test SA
    sa = SimulatedAnnealing(seed=42)
    sol = sa.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
        max_iterations=100,
        time_limit_ms=100.0,
    )
    print(f"  SA FSSP: makespan={sol.makespan}, iters={sol.iterations}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test ACO
    aco = AntColonyOptimization(n_ants=10, seed=42)
    sol = aco.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
        max_iterations=50,
        time_limit_ms=100.0,
    )
    print(f"  ACO FSSP: makespan={sol.makespan}, iters={sol.iterations}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test PSO
    pso = ParticleSwarmOptimization(n_particles=10, seed=42)
    sol = pso.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
        max_iterations=50,
        time_limit_ms=100.0,
    )
    print(f"  PSO FSSP: makespan={sol.makespan}, iters={sol.iterations}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_hybrid():
    print("=== Testing Hybrid Solvers ===")
    fssp_instance = create_test_fssp()

    # Test LNS
    lns = LargeNeighborhoodSearch(seed=42)
    sol = lns.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
        max_iterations=50,
        time_limit_ms=100.0,
    )
    print(f"  LNS FSSP: makespan={sol.makespan}, iters={sol.iterations}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test Matheuristic
    matheuristic = Matheuristic(time_limit_ms=100.0, seed=42)
    sol = matheuristic.solve_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
        max_iterations=20,
    )
    print(f"  Matheuristic FSSP: makespan={sol.makespan}, iters={sol.iterations}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


def test_learned():
    print("=== Testing Learned Solvers ===")
    jssp_instance = create_test_jssp()
    fssp_instance = create_test_fssp()

    # Test GNN
    gnn = GNNPredictor(hidden_dim=32, n_layers=2, seed=42)
    sol = gnn.predict_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
    )
    print(f"  GNN FSSP: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test RL
    rl = RLPolicy(hidden_dim=64, seed=42)
    sol = rl.predict_jssp(
        jssp_instance.n_jobs,
        jssp_instance.n_machines,
        jssp_instance.processing_times,
        jssp_instance.machine_sequence,
    )
    print(f"  RL JSSP: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    # Test Transformer
    transformer = TransformerScheduler(d_model=32, n_heads=4, n_layers=2, seed=42)
    sol = transformer.predict_fssp(
        fssp_instance.n_jobs,
        fssp_instance.n_machines,
        fssp_instance.processing_times,
    )
    print(f"  Transformer FSSP: makespan={sol.makespan}, time={sol.solve_time_us:.1f}us")
    assert sol.makespan > 0

    print("  ✓ PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("ULL Scheduling Optimization Kernel - Test Suite")
    print("=" * 60 + "\n")

    test_jssp()
    test_fssp()
    test_ossp()
    test_rcpsp()
    test_exact()
    test_approximation()
    test_metaheuristic()
    test_hybrid()
    test_learned()

    print("=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
