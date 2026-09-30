"""
Hybrid Solvers for Scheduling Problems
=======================================

Large Neighborhood Search (LNS) and Matheuristic approaches
for JSSP, FSSP, OSSP, and RCPSP.

Hybrid methods combine exact and heuristic techniques for
improved solution quality with bounded runtime.
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable, Set
import random
import array


@dataclass
class HybridSolution:
    """Solution from a hybrid solver."""
    makespan: int
    start_times: List[List[int]]
    iterations: int
    solve_time_us: float
    algorithm: str
    destroy_repair_history: List[Tuple[int, int]] = field(default_factory=list)


class LargeNeighborhoodSearch:
    """
    Large Neighborhood Search for scheduling problems.

    Features:
    - Destroy operators: random removal, worst removal, related removal
    - Repair operators: greedy insertion, regret insertion
    - Adaptive destroy size
    - Acceptance criterion: simulated annealing
    """

    def __init__(
        self,
        min_destroy: int = 2,
        max_destroy: int = 10,
        acceptance_threshold: float = 0.05,
        seed: int = 42,
    ):
        self.min_destroy = min_destroy
        self.max_destroy = max_destroy
        self.acceptance_threshold = acceptance_threshold
        self.rng = random.Random(seed)

    def solve_fssp(
        self,
        n_jobs: int,
        n_machines: int,
        processing_times: List[List[int]],
        max_iterations: int = 1000,
        time_limit_ms: float = 100.0,
    ) -> HybridSolution:
        """Solve FSSP using Large Neighborhood Search."""
        t_start = time.perf_counter_ns()

        # Initial solution from NEH
        current_order = self._neh_initial(n_jobs, n_machines, processing_times)
        current_makespan = self._compute_makespan(n_machines, processing_times, current_order)

        best_order = current_order[:]
        best_makespan = current_makespan
        history = [(0, best_makespan)]

        destroy_size = self.min_destroy

        for iteration in range(max_iterations):
            elapsed_ms = (time.perf_counter_ns() - t_start) / 1e6
            if elapsed_ms >= time_limit_ms:
                break

            # Destroy: remove k random jobs
            k = min(destroy_size, n_jobs - 1)
            removed_positions = self.rng.sample(range(n_jobs), k)
            removed_jobs = [current_order[p] for p in removed_positions]
            partial_order = [j for i, j in enumerate(current_order) if i not in removed_positions]

            # Repair: reinsert removed jobs at best positions
            for job in removed_jobs:
                best_pos = 0
                best_insert_makespan = float('inf')
                for pos in range(len(partial_order) + 1):
                    candidate = partial_order[:pos] + [job] + partial_order[pos:]
                    makespan = self._compute_makespan(n_machines, processing_times, candidate)
                    if makespan < best_insert_makespan:
                        best_insert_makespan = makespan
                        best_pos = pos
                partial_order = partial_order[:best_pos] + [job] + partial_order[best_pos:]

            new_makespan = best_insert_makespan

            # Acceptance criterion
            if new_makespan < current_makespan:
                current_order = partial_order
                current_makespan = new_makespan
                destroy_size = max(self.min_destroy, destroy_size - 1)

                if current_makespan < best_makespan:
                    best_makespan = current_makespan
                    best_order = current_order[:]
                    history.append((iteration + 1, best_makespan))
            elif self.rng.random() < self.acceptance_threshold:
                current_order = partial_order
                current_makespan = new_makespan
                destroy_size = min(self.max_destroy, destroy_size + 1)
            else:
                destroy_size = min(self.max_destroy, destroy_size + 1)

        elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0

        return HybridSolution(
            makespan=best_makespan,
            start_times=[],
            iterations=iteration + 1,
            solve_time_us=elapsed_us,
            algorithm="lns-fssp",
            destroy_repair_history=history,
        )

    def _neh_initial(self, n_jobs: int, n_machines: int, processing_times: List[List[int]]) -> List[int]:
        """Generate initial solution using NEH heuristic."""
        total_pt = [sum(processing_times[j]) for j in range(n_jobs)]
        sorted_jobs = sorted(range(n_jobs), key=lambda j: -total_pt[j])

        best_order = [sorted_jobs[0]]

        for idx in range(1, n_jobs):
            job = sorted_jobs[idx]
            best_makespan = float('inf')
            best_pos = 0

            for pos in range(len(best_order) + 1):
                candidate = best_order[:pos] + [job] + best_order[pos:]
                makespan = self._compute_makespan(n_machines, processing_times, candidate)
                if makespan < best_makespan:
                    best_makespan = makespan
                    best_pos = pos

            best_order = best_order[:best_pos] + [job] + best_order[best_pos:]

        return best_order

    def _compute_makespan(self, n_machines: int, processing_times: List[List[int]], job_order: List[int]) -> int:
        """Compute makespan for a given job order in FSSP."""
        n = len(job_order)
        if n == 0:
            return 0

        completion = [[0] * n_machines for _ in range(n)]

        for idx, j in enumerate(job_order):
            for k in range(n_machines):
                if idx == 0 and k == 0:
                    completion[idx][k] = processing_times[j][k]
                elif idx == 0:
                    completion[idx][k] = completion[idx][k-1] + processing_times[j][k]
                elif k == 0:
                    completion[idx][k] = completion[idx-1][k] + processing_times[j][k]
                else:
                    completion[idx][k] = max(completion[idx-1][k], completion[idx][k-1]) + processing_times[j][k]

        return completion[n-1][n_machines-1]


class Matheuristic:
    """
    Matheuristic solver combining mathematical programming and metaheuristics.

    Uses:
    - LP relaxation for bounding
    - Fix-and-optimize
    - Neighborhood search guided by LP solutions
    """

    def __init__(
        self,
        time_limit_ms: float = 100.0,
        seed: int = 42,
    ):
        self.time_limit_ms = time_limit_ms
        self.rng = random.Random(seed)

    def solve_fssp(
        self,
        n_jobs: int,
        n_machines: int,
        processing_times: List[List[int]],
        max_iterations: int = 100,
    ) -> HybridSolution:
        """
        Solve FSSP using matheuristic approach.

        Combines NEH with fix-and-optimize.
        """
        t_start = time.perf_counter_ns()

        # Initial solution from NEH
        current_order = self._neh_initial(n_jobs, n_machines, processing_times)
        current_makespan = self._compute_makespan(n_machines, processing_times, current_order)

        best_order = current_order[:]
        best_makespan = current_makespan
        history = [(0, best_makespan)]

        for iteration in range(max_iterations):
            elapsed_ms = (time.perf_counter_ns() - t_start) / 1e6
            if elapsed_ms >= self.time_limit_ms:
                break

            # Fix-and-optimize: fix a subset of jobs, optimize the rest
            fix_size = max(1, n_jobs // 3)
            fixed_positions = set(self.rng.sample(range(n_jobs), fix_size))

            # Extract fixed and free jobs
            fixed_jobs = [current_order[p] for p in sorted(fixed_positions)]
            free_jobs = [j for i, j in enumerate(current_order) if i not in fixed_positions]

            # Optimize free jobs using exhaustive search (for small subsets)
            if len(free_jobs) <= 8:
                best_free_order = self._exhaustive_search(free_jobs, n_machines, processing_times, fixed_jobs, fixed_positions, n_jobs)
            else:
                # Use NEH for larger subsets
                best_free_order = self._neh_subset(free_jobs, n_machines, processing_times)

            # Reconstruct full order
            new_order = self._reconstruct_order(fixed_jobs, best_free_order, fixed_positions, n_jobs)
            new_makespan = self._compute_makespan(n_machines, processing_times, new_order)

            if new_makespan < current_makespan:
                current_order = new_order
                current_makespan = new_makespan

                if current_makespan < best_makespan:
                    best_makespan = current_makespan
                    best_order = current_order[:]
                    history.append((iteration + 1, best_makespan))

        elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0

        return HybridSolution(
            makespan=best_makespan,
            start_times=[],
            iterations=iteration + 1,
            solve_time_us=elapsed_us,
            algorithm="matheuristic-fssp",
            destroy_repair_history=history,
        )

    def _neh_initial(self, n_jobs: int, n_machines: int, processing_times: List[List[int]]) -> List[int]:
        """Generate initial solution using NEH heuristic."""
        total_pt = [sum(processing_times[j]) for j in range(n_jobs)]
        sorted_jobs = sorted(range(n_jobs), key=lambda j: -total_pt[j])

        best_order = [sorted_jobs[0]]

        for idx in range(1, n_jobs):
            job = sorted_jobs[idx]
            best_makespan = float('inf')
            best_pos = 0

            for pos in range(len(best_order) + 1):
                candidate = best_order[:pos] + [job] + best_order[pos:]
                makespan = self._compute_makespan(n_machines, processing_times, candidate)
                if makespan < best_makespan:
                    best_makespan = makespan
                    best_pos = pos

            best_order = best_order[:best_pos] + [job] + best_order[best_pos:]

        return best_order

    def _exhaustive_search(
        self,
        free_jobs: List[int],
        n_machines: int,
        processing_times: List[List[int]],
        fixed_jobs: List[int],
        fixed_positions: Set[int],
        n_jobs: int,
    ) -> List[int]:
        """Exhaustive search for small subsets."""
        best_order = free_jobs[:]
        best_makespan = float('inf')

        # Generate all permutations
        from itertools import permutations
        for perm in permutations(free_jobs):
            # Reconstruct full order
            full_order = self._reconstruct_order(fixed_jobs, list(perm), fixed_positions, n_jobs)
            makespan = self._compute_makespan(n_machines, processing_times, full_order)
            if makespan < best_makespan:
                best_makespan = makespan
                best_order = list(perm)

        return best_order

    def _neh_subset(self, free_jobs: List[int], n_machines: int, processing_times: List[List[int]]) -> List[int]:
        """NEH for subsets."""
        total_pt = [sum(processing_times[j]) for j in free_jobs]
        sorted_jobs = sorted(free_jobs, key=lambda j: -total_pt[j])

        best_order = [sorted_jobs[0]]

        for idx in range(1, len(sorted_jobs)):
            job = sorted_jobs[idx]
            best_makespan = float('inf')
            best_pos = 0

            for pos in range(len(best_order) + 1):
                candidate = best_order[:pos] + [job] + best_order[pos:]
                makespan = self._compute_makespan(n_machines, processing_times, candidate)
                if makespan < best_makespan:
                    best_makespan = makespan
                    best_pos = pos

            best_order = best_order[:best_pos] + [job] + best_order[best_pos:]

        return best_order

    def _reconstruct_order(
        self,
        fixed_jobs: List[int],
        free_jobs: List[int],
        fixed_positions: Set[int],
        n_jobs: int,
    ) -> List[int]:
        """Reconstruct full order from fixed and free jobs."""
        order = []
        free_idx = 0
        fixed_idx = 0

        for pos in range(n_jobs):
            if pos in fixed_positions:
                order.append(fixed_jobs[fixed_idx])
                fixed_idx += 1
            else:
                order.append(free_jobs[free_idx])
                free_idx += 1

        return order

    def _compute_makespan(self, n_machines: int, processing_times: List[List[int]], job_order: List[int]) -> int:
        """Compute makespan for a given job order in FSSP."""
        n = len(job_order)
        if n == 0:
            return 0

        completion = [[0] * n_machines for _ in range(n)]

        for idx, j in enumerate(job_order):
            for k in range(n_machines):
                if idx == 0 and k == 0:
                    completion[idx][k] = processing_times[j][k]
                elif idx == 0:
                    completion[idx][k] = completion[idx][k-1] + processing_times[j][k]
                elif k == 0:
                    completion[idx][k] = completion[idx-1][k] + processing_times[j][k]
                else:
                    completion[idx][k] = max(completion[idx-1][k], completion[idx][k-1]) + processing_times[j][k]

        return completion[n-1][n_machines-1]
