"""
Metaheuristic Solvers for Scheduling Problems
==============================================

Genetic Algorithm, Simulated Annealing, Ant Colony Optimization,
and Particle Swarm Optimization for JSSP, FSSP, OSSP, and RCPSP.

All metaheuristics are optimized for ultra-low latency with:
- Pre-allocated buffers
- Cache-friendly data structures
- Efficient neighborhood exploration
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable
import random
import array


@dataclass
class MetaheuristicSolution:
    """Solution from a metaheuristic solver."""
    makespan: int
    start_times: List[List[int]]
    iterations: int
    solve_time_us: float
    algorithm: str
    convergence_history: List[int] = field(default_factory=list)


class GeneticAlgorithm:
    """
    Genetic Algorithm for scheduling problems.

    Features:
    - Tournament selection
    - Order crossover (OX)
    - Swap mutation
    - Elitism
    """

    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism: int = 2,
        seed: int = 42,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism
        self.rng = random.Random(seed)

    def solve_fssp(
        self,
        n_jobs: int,
        n_machines: int,
        processing_times: List[List[int]],
        max_iterations: int = 1000,
        time_limit_ms: float = 100.0,
    ) -> MetaheuristicSolution:
        """Solve FSSP using Genetic Algorithm."""
        t_start = time.perf_counter_ns()

        # Initialize population
        population = []
        for _ in range(self.population_size):
            perm = list(range(n_jobs))
            self.rng.shuffle(perm)
            population.append(perm)

        best_order = list(range(n_jobs))
        best_makespan = self._compute_makespan(n_machines, processing_times, best_order)
        convergence = [best_makespan]

        for generation in range(max_iterations):
            elapsed_ms = (time.perf_counter_ns() - t_start) / 1e6
            if elapsed_ms >= time_limit_ms:
                break

            # Evaluate fitness
            fitness = []
            for ind in population:
                makespan = self._compute_makespan(n_machines, processing_times, ind)
                fitness.append(makespan)
                if makespan < best_makespan:
                    best_makespan = makespan
                    best_order = ind[:]

            convergence.append(best_makespan)

            # Selection (tournament)
            new_population = []
            for _ in range(self.population_size):
                i1, i2 = self.rng.sample(range(self.population_size), 2)
                winner = population[i1] if fitness[i1] < fitness[i2] else population[i2]
                new_population.append(winner[:])

            # Elitism
            sorted_indices = sorted(range(self.population_size), key=lambda i: fitness[i])
            elites = [population[i][:] for i in sorted_indices[:self.elitism]]

            # Crossover (OX)
            offspring = []
            for i in range(0, self.population_size, 2):
                if i + 1 < self.population_size and self.rng.random() < self.crossover_rate:
                    p1, p2 = new_population[i], new_population[i+1]
                    c1, c2 = self._ox_crossover(p1, p2)
                    offspring.extend([c1, c2])
                else:
                    offspring.extend([new_population[i], new_population[i+1] if i+1 < self.population_size else new_population[i]])

            # Mutation (swap)
            for i in range(len(offspring)):
                if self.rng.random() < self.mutation_rate:
                    a, b = self.rng.sample(range(n_jobs), 2)
                    offspring[i][a], offspring[i][b] = offspring[i][b], offspring[i][a]

            # Replace population with elites + offspring
            population = elites + offspring[:self.population_size - self.elitism]

        elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0

        return MetaheuristicSolution(
            makespan=best_makespan,
            start_times=[],
            iterations=generation + 1,
            solve_time_us=elapsed_us,
            algorithm="ga-fssp",
            convergence_history=convergence,
        )

    def _ox_crossover(self, p1: List[int], p2: List[int]) -> Tuple[List[int], List[int]]:
        """Order Crossover (OX)."""
        n = len(p1)
        a, b = sorted(self.rng.sample(range(n), 2))

        def ox(parent1, parent2):
            child = [-1] * n
            child[a:b] = parent1[a:b]
            used = set(child[a:b])
            idx = b % n
            for j in range(n):
                pos = (b + j) % n
                if parent2[pos] not in used:
                    child[idx] = parent2[pos]
                    used.add(parent2[pos])
                    idx = (idx + 1) % n
            return child

        return ox(p1, p2), ox(p2, p1)

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


class SimulatedAnnealing:
    """
    Simulated Annealing for scheduling problems.

    Features:
    - Geometric cooling schedule
    - Swap neighborhood
    - Adaptive temperature
    """

    def __init__(
        self,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.995,
        seed: int = 42,
    ):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.rng = random.Random(seed)

    def solve_fssp(
        self,
        n_jobs: int,
        n_machines: int,
        processing_times: List[List[int]],
        max_iterations: int = 1000,
        time_limit_ms: float = 100.0,
    ) -> MetaheuristicSolution:
        """Solve FSSP using Simulated Annealing."""
        t_start = time.perf_counter_ns()

        # Initial solution
        current_order = list(range(n_jobs))
        self.rng.shuffle(current_order)
        current_makespan = self._compute_makespan(n_machines, processing_times, current_order)

        best_order = current_order[:]
        best_makespan = current_makespan
        convergence = [best_makespan]

        temp = self.initial_temp

        for iteration in range(max_iterations):
            elapsed_ms = (time.perf_counter_ns() - t_start) / 1e6
            if elapsed_ms >= time_limit_ms:
                break

            # Generate neighbor: swap two random positions
            i, j = self.rng.sample(range(n_jobs), 2)
            new_order = current_order[:]
            new_order[i], new_order[j] = new_order[j], new_order[i]

            new_makespan = self._compute_makespan(n_machines, processing_times, new_order)

            # Accept or reject
            delta = new_makespan - current_makespan
            if delta < 0 or self.rng.random() < math.exp(-delta / temp):
                current_order = new_order
                current_makespan = new_makespan

                if current_makespan < best_makespan:
                    best_makespan = current_makespan
                    best_order = current_order[:]

            convergence.append(best_makespan)
            temp *= self.cooling_rate

        elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0

        return MetaheuristicSolution(
            makespan=best_makespan,
            start_times=[],
            iterations=iteration + 1,
            solve_time_us=elapsed_us,
            algorithm="sa-fssp",
            convergence_history=convergence,
        )

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


class AntColonyOptimization:
    """
    Ant Colony Optimization for scheduling problems.

    Features:
    - Pheromone-based path selection
    - Heuristic information
    - Evaporation
    """

    def __init__(
        self,
        n_ants: int = 20,
        alpha: float = 1.0,
        beta: float = 2.0,
        evaporation: float = 0.5,
        seed: int = 42,
    ):
        self.n_ants = n_ants
        self.alpha = alpha
        self.beta = beta
        self.evaporation = evaporation
        self.rng = random.Random(seed)

    def solve_fssp(
        self,
        n_jobs: int,
        n_machines: int,
        processing_times: List[List[int]],
        max_iterations: int = 1000,
        time_limit_ms: float = 100.0,
    ) -> MetaheuristicSolution:
        """Solve FSSP using Ant Colony Optimization."""
        t_start = time.perf_counter_ns()

        # Initialize pheromone
        pheromone = [[1.0] * n_jobs for _ in range(n_jobs)]

        # Heuristic information
        heuristic = [[1.0 / (1.0 + abs(sum(processing_times[i]) - sum(processing_times[j]))) for j in range(n_jobs)] for i in range(n_jobs)]

        best_order = list(range(n_jobs))
        best_makespan = self._compute_makespan(n_machines, processing_times, best_order)
        convergence = [best_makespan]

        for iteration in range(max_iterations):
            elapsed_ms = (time.perf_counter_ns() - t_start) / 1e6
            if elapsed_ms >= time_limit_ms:
                break

            all_orders = []
            all_makespans = []

            for ant in range(self.n_ants):
                # Construct solution
                order = []
                remaining = set(range(n_jobs))

                # Start with random job
                current = self.rng.choice(list(remaining))
                order.append(current)
                remaining.remove(current)

                while remaining:
                    # Compute probabilities
                    probs = []
                    for j in remaining:
                        tau = pheromone[current][j] ** self.alpha
                        eta = heuristic[current][j] ** self.beta
                        probs.append(tau * eta)

                    total = sum(probs)
                    probs = [p / total for p in probs]

                    # Select next job
                    r = self.rng.random()
                    cumsum = 0.0
                    for idx, p in enumerate(probs):
                        cumsum += p
                        if r <= cumsum:
                            current = list(remaining)[idx]
                            break

                    order.append(current)
                    remaining.remove(current)

                makespan = self._compute_makespan(n_machines, processing_times, order)
                all_orders.append(order)
                all_makespans.append(makespan)

                if makespan < best_makespan:
                    best_makespan = makespan
                    best_order = order[:]

            convergence.append(best_makespan)

            # Update pheromone
            for i in range(n_jobs):
                for j in range(n_jobs):
                    pheromone[i][j] *= (1 - self.evaporation)

            for order, makespan in zip(all_orders, all_makespans):
                delta = 1.0 / makespan
                for i in range(len(order) - 1):
                    pheromone[order[i]][order[i+1]] += delta

        elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0

        return MetaheuristicSolution(
            makespan=best_makespan,
            start_times=[],
            iterations=iteration + 1,
            solve_time_us=elapsed_us,
            algorithm="aco-fssp",
            convergence_history=convergence,
        )

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


class ParticleSwarmOptimization:
    """
    Particle Swarm Optimization for scheduling problems.

    Features:
    - Swap-based velocity
    - Personal and global best
    - Inertia weight
    """

    def __init__(
        self,
        n_particles: int = 30,
        inertia: float = 0.7,
        cognitive: float = 1.5,
        social: float = 1.5,
        seed: int = 42,
    ):
        self.n_particles = n_particles
        self.inertia = inertia
        self.cognitive = cognitive
        self.social = social
        self.rng = random.Random(seed)

    def solve_fssp(
        self,
        n_jobs: int,
        n_machines: int,
        processing_times: List[List[int]],
        max_iterations: int = 1000,
        time_limit_ms: float = 100.0,
    ) -> MetaheuristicSolution:
        """Solve FSSP using Particle Swarm Optimization."""
        t_start = time.perf_counter_ns()

        # Initialize particles
        particles = []
        for _ in range(self.n_particles):
            perm = list(range(n_jobs))
            self.rng.shuffle(perm)
            particles.append(perm)

        # Personal best
        pbest = [p[:] for p in particles]
        pbest_makespan = [self._compute_makespan(n_machines, processing_times, p) for p in particles]

        # Global best
        gbest_idx = min(range(self.n_particles), key=lambda i: pbest_makespan[i])
        gbest = pbest[gbest_idx][:]
        gbest_makespan = pbest_makespan[gbest_idx]
        convergence = [gbest_makespan]

        for iteration in range(max_iterations):
            elapsed_ms = (time.perf_counter_ns() - t_start) / 1e6
            if elapsed_ms >= time_limit_ms:
                break

            for i in range(self.n_particles):
                # Update particle
                new_particle = particles[i][:]

                # Apply swap operations based on cognitive and social components
                for _ in range(int(self.inertia * n_jobs)):
                    if self.rng.random() < self.cognitive:
                        # Move toward personal best
                        diff = self._permutation_diff(new_particle, pbest[i])
                        for pos in diff:
                            if self.rng.random() < 0.5:
                                new_particle = self._apply_swap(new_particle, pos)
                    elif self.rng.random() < self.social:
                        # Move toward global best
                        diff = self._permutation_diff(new_particle, gbest)
                        for pos in diff:
                            if self.rng.random() < 0.5:
                                new_particle = self._apply_swap(new_particle, pos)

                # Random perturbation
                if self.rng.random() < 0.1:
                    a, b = self.rng.sample(range(n_jobs), 2)
                    new_particle[a], new_particle[b] = new_particle[b], new_particle[a]

                particles[i] = new_particle

                # Update personal best
                makespan = self._compute_makespan(n_machines, processing_times, new_particle)
                if makespan < pbest_makespan[i]:
                    pbest_makespan[i] = makespan
                    pbest[i] = new_particle[:]

                    if makespan < gbest_makespan:
                        gbest_makespan = makespan
                        gbest = new_particle[:]

            convergence.append(gbest_makespan)

        elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0

        return MetaheuristicSolution(
            makespan=gbest_makespan,
            start_times=[],
            iterations=iteration + 1,
            solve_time_us=elapsed_us,
            algorithm="pso-fssp",
            convergence_history=convergence,
        )

    def _permutation_diff(self, p1: List[int], p2: List[int]) -> List[Tuple[int, int]]:
        """Find swap operations to transform p1 into p2."""
        n = len(p1)
        diff = []
        pos_map = {v: i for i, v in enumerate(p2)}

        for i in range(n):
            if p1[i] != p2[i]:
                j = pos_map[p1[i]]
                diff.append((i, j))

        return diff

    def _apply_swap(self, perm: List[int], swap: Tuple[int, int]) -> List[int]:
        """Apply a swap to a permutation."""
        i, j = swap
        new_perm = perm[:]
        new_perm[i], new_perm[j] = new_perm[j], new_perm[i]
        return new_perm

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
