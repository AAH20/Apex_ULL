"""
ULL Scheduling Optimization Kernel
===================================

Ultra-low-latency scheduling kernels for JSSP, FSSP, OSSP, and RCPSP.

Problem domains:
- JSSP: Job Shop Scheduling Problem (makespan minimization)
- FSSP: Flow Shop Scheduling Problem (permutation, makespan minimization)
- OSSP: Open Shop Scheduling Problem (makespan minimization)
- RCPSP: Resource-Constrained Project Scheduling Problem

Solver categories:
- Exact: Branch & Bound, Dynamic Programming, ILP
- Approximation: PTAS, FPTAS, Rounding
- Metaheuristic: GA, SA, ACO, PSO
- Hybrid: LNS, Matheuristic
- Learned: GNN, RL, Transformer

Each solver is optimized for minimal latency: pre-allocated buffers,
cache-friendly data structures, and branch-free inner loops where possible.
"""

from .jssp import JSSPSolver, JSSPInstance, JSSPSolution
from .fssp import FSSPSolver, FSSPInstance, FSSPSolution
from .ossp import OSSPSolver, OSSPInstance, OSSPSolution
from .rcpsp import RCPSPSolver, RCPSPInstance, RCPSPSolution
from .exact import BranchAndBound, DynamicProgramming, IntegerLinearProgramming, ExactSolution
from .approximation import PTAS, FPTAS, RoundingScheme, ApproxSolution
from .metaheuristic import GeneticAlgorithm, SimulatedAnnealing, AntColonyOptimization, ParticleSwarmOptimization, MetaheuristicSolution
from .hybrid import LargeNeighborhoodSearch, Matheuristic, HybridSolution
from .learned import GNNPredictor, RLPolicy, TransformerScheduler, LearnedSolution

__all__ = [
    # JSSP
    "JSSPSolver", "JSSPInstance", "JSSPSolution",
    # FSSP
    "FSSPSolver", "FSSPInstance", "FSSPSolution",
    # OSSP
    "OSSPSolver", "OSSPInstance", "OSSPSolution",
    # RCPSP
    "RCPSPSolver", "RCPSPInstance", "RCPSPSolution",
    # Exact
    "BranchAndBound", "DynamicProgramming", "IntegerLinearProgramming", "ExactSolution",
    # Approximation
    "PTAS", "FPTAS", "RoundingScheme", "ApproxSolution",
    # Metaheuristic
    "GeneticAlgorithm", "SimulatedAnnealing", "AntColonyOptimization", "ParticleSwarmOptimization", "MetaheuristicSolution",
    # Hybrid
    "LargeNeighborhoodSearch", "Matheuristic", "HybridSolution",
    # Learned
    "GNNPredictor", "RLPolicy", "TransformerScheduler", "LearnedSolution",
]
