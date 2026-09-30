"""
STAC-A2: Risk Computation Benchmark

Measures the latency of pre-trade risk checks, including position limits,
notional exposure, and Greeks computation for options.

Reference values (from research):
  - FPGA risk check:           ~200-500 ns
  - CPU optimized (C++):       ~1-5 μs
  - Standard Python:           ~50-200 μs

Scoring: Multi-dimensional composite with:
  - Latency (p50): 40% weight
  - Throughput: 15% weight
  - Jitter: 5% weight
  - Tail latency (p99): 20% weight
  - Consistency (CV): 20% weight
Reference p50: 500 ns (FPGA-class risk check).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from common.harness import (
    run_benchmark,
    BenchmarkResult,
    compute_score_breakdown,
    get_environment_info,
    now_ns,
)
from common.metrics import MetricDef


# ---------------------------------------------------------------------------
# Benchmark-specific metrics
# ---------------------------------------------------------------------------

STAC_A2_METRICS = [
    MetricDef("position_check_ns", "ns", "Position limit check latency", "lower_is_better", 100.0),
    MetricDef("notional_check_ns", "ns", "Notional exposure check latency", "lower_is_better", 100.0),
    MetricDef("greeks_ns", "ns", "Greeks computation latency", "lower_is_better", 200.0),
    MetricDef("risk_checks_per_second", "checks/s", "Sustained risk check rate", "higher_is_better", 1_000_000.0),
    MetricDef("max_position", "units", "Maximum allowed position", "lower_is_better", 10000.0),
]


# ---------------------------------------------------------------------------
# Simulated risk engine
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Position:
    """Current position in a symbol."""
    symbol_id: int
    quantity: int
    avg_price: float


@dataclass(slots=True)
class OrderRequest:
    """Proposed order to risk-check."""
    symbol_id: int
    side: int  # 0=buy, 1=sell
    quantity: int
    price: float


@dataclass(slots=True)
class Greeks:
    """Option Greeks."""
    delta: float
    gamma: float
    theta: float
    vega: float


class RiskEngine:
    """
    Pre-trade risk computation engine.

    Performs:
    1. Position limit check
    2. Notional exposure check
    3. Greeks computation (for options)
    4. Fat-finger check (price sanity)
    """

    def __init__(self, max_position: int = 10_000, max_notional: float = 10_000_000.0):
        self.max_position = max_position
        self.max_notional = max_notional
        self._positions: dict[int, Position] = {}
        self._total_notional: float = 0.0
        # Pre-generate order requests
        self._order_templates = self._generate_order_templates()

    def _generate_order_templates(self) -> list[OrderRequest]:
        """Generate realistic order requests."""
        orders = []
        for _ in range(1000):
            orders.append(OrderRequest(
                symbol_id=random.randint(0, 99),
                side=random.randint(0, 1),
                quantity=random.randint(1, 5000),
                price=random.uniform(100.0, 10000.0),
            ))
        return orders

    def check_position_limit(self, order: OrderRequest) -> bool:
        """Check if order would exceed position limit."""
        current = self._positions.get(order.symbol_id)
        current_qty = current.quantity if current else 0
        new_qty = current_qty + order.quantity if order.side == 0 else current_qty - order.quantity
        return abs(new_qty) <= self.max_position

    def check_notional_exposure(self, order: OrderRequest) -> bool:
        """Check if order would exceed notional exposure limit."""
        order_notional = order.quantity * order.price
        return (self._total_notional + order_notional) <= self.max_notional

    def compute_greeks(self, spot: float, strike: float, time_to_expiry: float,
                       volatility: float, rate: float = 0.05) -> Greeks:
        """
        Compute option Greeks using Black-Scholes.
        Simplified for benchmark purposes.
        """
        if time_to_expiry <= 0 or volatility <= 0 or spot <= 0:
            return Greeks(delta=0.0, gamma=0.0, theta=0.0, vega=0.0)

        d1 = (math.log(spot / strike) + (rate + 0.5 * volatility ** 2) * time_to_expiry) / (
            volatility * math.sqrt(time_to_expiry)
        )
        d2 = d1 - volatility * math.sqrt(time_to_expiry)

        # Simplified Greeks (using approximations for speed)
        delta = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
        gamma = math.exp(-0.5 * d1 ** 2) / (spot * volatility * math.sqrt(2 * math.pi * time_to_expiry))
        theta = -(spot * gamma * volatility) / (2 * math.sqrt(time_to_expiry))
        vega = spot * math.sqrt(time_to_expiry) * math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)

        return Greeks(delta=delta, gamma=gamma, theta=theta, vega=vega)

    def check_fat_finger(self, order: OrderRequest, mid_price: float) -> bool:
        """Fat-finger check: order price within reasonable bounds of mid."""
        if mid_price <= 0:
            return False
        deviation = abs(order.price - mid_price) / mid_price
        return deviation <= 0.10  # 10% max deviation

    def risk_check(self, order: OrderRequest, spot: float = 50000.0,
                   strike: float = 50000.0, time_to_expiry: float = 0.25,
                   volatility: float = 0.20) -> dict[str, any]:
        """Full risk check pipeline."""
        # Position limit check
        pos_ok = self.check_position_limit(order)

        # Notional exposure check
        notional_ok = self.check_notional_exposure(order)

        # Fat-finger check
        mid_price = spot  # Simplified
        finger_ok = self.check_fat_finger(order, mid_price)

        # Greeks computation
        greeks = self.compute_greeks(spot, strike, time_to_expiry, volatility)

        # Update position if all checks pass
        all_ok = pos_ok and notional_ok and finger_ok
        if all_ok:
            current = self._positions.get(order.symbol_id)
            if current is None:
                self._positions[order.symbol_id] = Position(
                    symbol_id=order.symbol_id,
                    quantity=order.quantity if order.side == 0 else -order.quantity,
                    avg_price=order.price,
                )
            else:
                new_qty = current.quantity + (order.quantity if order.side == 0 else -order.quantity)
                current.quantity = new_qty
            self._total_notional += order.quantity * order.price

        return {
            "approved": all_ok,
            "position_ok": pos_ok,
            "notional_ok": notional_ok,
            "fat_finger_ok": finger_ok,
            "greeks": greeks,
        }

    def risk_check_timed(self, order: OrderRequest, spot: float = 50000.0,
                         strike: float = 50000.0, time_to_expiry: float = 0.25,
                         volatility: float = 0.20) -> tuple[dict[str, any], dict[str, int]]:
        """Risk check with per-stage timing."""
        t0 = now_ns()
        pos_ok = self.check_position_limit(order)
        t1 = now_ns()
        notional_ok = self.check_notional_exposure(order)
        t2 = now_ns()
        mid_price = spot
        finger_ok = self.check_fat_finger(order, mid_price)
        t3 = now_ns()
        greeks = self.compute_greeks(spot, strike, time_to_expiry, volatility)
        t4 = now_ns()

        all_ok = pos_ok and notional_ok and finger_ok
        if all_ok:
            current = self._positions.get(order.symbol_id)
            if current is None:
                self._positions[order.symbol_id] = Position(
                    symbol_id=order.symbol_id,
                    quantity=order.quantity if order.side == 0 else -order.quantity,
                    avg_price=order.price,
                )
            else:
                new_qty = current.quantity + (order.quantity if order.side == 0 else -order.quantity)
                current.quantity = new_qty
            self._total_notional += order.quantity * order.price

        result = {
            "approved": all_ok,
            "position_ok": pos_ok,
            "notional_ok": notional_ok,
            "fat_finger_ok": finger_ok,
            "greeks": greeks,
        }
        timings = {
            "position_check_ns": t1 - t0,
            "notional_check_ns": t2 - t1,
            "fat_finger_ns": t3 - t2,
            "greeks_ns": t4 - t3,
        }
        return result, timings


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def run_stac_a2(
    iterations: int = 500_000,
    warmup_iterations: int = 50_000,
    max_position: int = 10_000,
) -> BenchmarkResult:
    """
    Run STAC-A2: Risk Computation Benchmark.

    Measures latency of pre-trade risk checks including position limits,
    notional exposure, and Greeks computation.
    """
    engine = RiskEngine(max_position=max_position)
    templates = engine._order_templates
    num_templates = len(templates)

    # Sub-stage timing accumulators
    position_check_times: list[int] = []
    notional_check_times: list[int] = []
    fat_finger_times: list[int] = []
    greeks_times: list[int] = []

    def operation():
        order = templates[random.randint(0, num_templates - 1)]
        _, timings = engine.risk_check_timed(order)
        position_check_times.append(timings["position_check_ns"])
        notional_check_times.append(timings["notional_check_ns"])
        fat_finger_times.append(timings["fat_finger_ns"])
        greeks_times.append(timings["greeks_ns"])
        return None

    def detailed_scoring(stats, iters, duration):
        return compute_score_breakdown(
            stats, iters, duration,
            latency_weight=0.4,
            throughput_weight=0.15,
            jitter_weight=0.05,
            tail_latency_weight=0.2,
            consistency_weight=0.2,
            reference_p50_ns=500.0,       # FPGA-class risk check
            reference_throughput=1_000_000.0,  # 1M checks/sec
            reference_jitter_ns=50.0,
            reference_p99_ns=2000.0,
            reference_cv=0.3,
        )

    result = run_benchmark(
        name="STAC-A2",
        version="2.0.0",
        description="Risk Computation: pre-trade risk checks (position, notional, Greeks)",
        fn=operation,
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        detailed_scoring_fn=detailed_scoring,
        metadata={
            "max_position": max_position,
            "max_notional": engine.max_notional,
            "checks_performed": ["position_limit", "notional_exposure", "fat_finger", "greeks"],
            "sub_stage_timing": {
                "position_check_ns_avg": sum(position_check_times) / len(position_check_times) if position_check_times else 0,
                "notional_check_ns_avg": sum(notional_check_times) / len(notional_check_times) if notional_check_times else 0,
                "fat_finger_ns_avg": sum(fat_finger_times) / len(fat_finger_times) if fat_finger_times else 0,
                "greeks_ns_avg": sum(greeks_times) / len(greeks_times) if greeks_times else 0,
            },
            "environment": get_environment_info(),
        },
    )
    return result


if __name__ == "__main__":
    result = run_stac_a2()
    print(result.to_json())
