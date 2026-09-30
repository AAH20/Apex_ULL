"""Finite generated precedence and resource invariants for the scheduling solver."""
import random
import unittest
from kernels.scheduling.jssp import JSSPInstance, JSSPSolver

class SchedulingProperties(unittest.TestCase):
    def test_generated_schedules(self):
        rng=random.Random(42)
        for jobs in range(2,6):
            for machines in range(2,6):
                durations=[[rng.randint(1,10) for _ in range(machines)] for _ in range(jobs)]
                order=[rng.sample(range(machines),machines) for _ in range(jobs)]
                instance=JSSPInstance(jobs,machines,durations,order)
                solution=JSSPSolver(seed=42).solve(instance,algorithm="gt")
                self.assertIsNotNone(solution)
                intervals=[[] for _ in range(machines)]
                completions=[]
                for job in range(jobs):
                    for operation in range(machines):
                        start=solution.start_times[job][operation]
                        finish=start+durations[job][operation]
                        self.assertGreaterEqual(start,0)
                        if operation:
                            self.assertGreaterEqual(start,solution.start_times[job][operation-1]+durations[job][operation-1])
                        intervals[order[job][operation]].append((start,finish))
                        completions.append(finish)
                for entries in intervals:
                    ordered=sorted(entries)
                    for previous,current in zip(ordered,ordered[1:]):
                        self.assertLessEqual(previous[1],current[0])
                self.assertEqual(solution.makespan,max(completions))
