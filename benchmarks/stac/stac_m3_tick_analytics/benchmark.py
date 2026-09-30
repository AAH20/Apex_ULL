"""
STAC-M3: Tick Analytics Benchmark

Measures the latency of computing real-time analytics on a stream of
market data ticks, including VWAP, moving averages, and volatility.

Reference values (from research):
  - FPGA tick analytics:       ~1.2 μs per tick (Jump Trading)
  - CPU optimized:             ~5-20 μs per tick
  - Standard Python:           ~50-200 μs per tick

Scoring: Multi-dimensional composite with:
  - Latency (p50): 30% weight
  - Throughput: 30% weight
  - Jitter: 10% weight
  - Tail latency (p99): 15% weight
  - Consistency (CV): 15% weight
Reference p50: 1200 ns (FPGA-class tick analytics).
"""

from __future__ import annotations

import math
import random
import struct
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

STAC_M3_METRICS = [
    MetricDef("vwap_ns", "ns", "VWAP computation latency", "lower_is_better", 300.0),
    MetricDef("sma_ns", "ns", "Simple moving average latency", "lower_is_better", 200.0),
    MetricDef("volatility_ns", "ns", "Rolling volatility latency", "lower_is_better", 400.0),
    MetricDef("analytics_per_second", "ops/s", "Sustained analytics computation rate", "higher_is_better", 500_000.0),
    MetricDef("window_size", "ticks", "Rolling window size for analytics", "lower_is_better", 100.0),
]


# ---------------------------------------------------------------------------
# Simulated tick analytics engine
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Tick:
    """Single market data tick."""
    timestamp_ns: int
    price: int
    quantity: int


class TickAnalytics:
    """
    Real-time tick analytics engine.

    Computes on each tick:
    1. VWAP (Volume-Weighted Average Price) over rolling window
    2. Simple Moving Average (SMA) over rolling window
    3. Rolling volatility (standard deviation of returns)
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._prices: list[int] = []
        self._quantities: list[int] = []
        self._returns: list[float] = []
        self._last_price: int | None = None
        # Pre-generate tick stream
        self._tick_stream = self._generate_tick_stream()

    def _generate_tick_stream(self) -> list[Tick]:
        """Generate a realistic tick stream."""
        ticks = []
        base_price = 500000  # $5000.00 in 1/100th cent
        for i in range(1000):
            # Random walk with mean reversion
            change = random.gauss(0, 50)
            price = max(10000, base_price + int(change))
            qty = random.randint(1, 5000)
            ts = 1_700_000_000_000_000_000 + i * 1_000_000  # 1ms apart
            ticks.append(Tick(timestamp_ns=ts, price=price, quantity=qty))
            base_price = price
        return ticks

    def compute_vwap(self) -> float:
        """Compute Volume-Weighted Average Price over rolling window."""
        if not self._prices:
            return 0.0
        total_pq = sum(p * q for p, q in zip(self._prices, self._quantities))
        total_q = sum(self._quantities)
        return total_pq / total_q if total_q > 0 else 0.0

    def compute_sma(self) -> float:
        """Compute Simple Moving Average over rolling window."""
        if not self._prices:
            return 0.0
        return sum(self._prices) / len(self._prices)

    def compute_volatility(self) -> float:
        """Compute rolling volatility (std dev of log returns)."""
        if len(self._returns) < 2:
            return 0.0
        mean_ret = sum(self._returns) / len(self._returns)
        variance = sum((r - mean_ret) ** 2 for r in self._returns) / (len(self._returns) - 1)
        return math.sqrt(variance)

    def process_tick(self, tick: Tick) -> dict[str, float]:
        """Process a single tick and compute all analytics."""
        # Update rolling window
        self._prices.append(tick.price)
        self._quantities.append(tick.quantity)
        if len(self._prices) > self.window_size:
            self._prices.pop(0)
            self._quantities.pop(0)

        # Compute log return
        if self._last_price is not None and self._last_price > 0:
            log_ret = math.log(tick.price / self._last_price)
            self._returns.append(log_ret)
            if len(self._returns) > self.window_size:
                self._returns.pop(0)
        self._last_price = tick.price

        # Compute all analytics
        return {
            "vwap": self.compute_vwap(),
            "sma": self.compute_sma(),
            "volatility": self.compute_volatility(),
        }

    def process_tick_timed(self, tick: Tick) -> tuple[dict[str, float], dict[str, int]]:
        """Process tick with per-stage timing."""
        t0 = now_ns()
        # Update rolling window
        self._prices.append(tick.price)
        self._quantities.append(tick.quantity)
        if len(self._prices) > self.window_size:
            self._prices.pop(0)
            self._quantities.pop(0)
        t1 = now_ns()
        # Compute log return
        if self._last_price is not None and self._last_price > 0:
            log_ret = math.log(tick.price / self._last_price)
            self._returns.append(log_ret)
            if len(self._returns) > self.window_size:
                self._returns.pop(0)
        self._last_price = tick.price
        t2 = now_ns()
        # Compute all analytics
        result = {
            "vwap": self.compute_vwap(),
            "sma": self.compute_sma(),
            "volatility": self.compute_volatility(),
        }
        t3 = now_ns()
        return result, {
            "window_update_ns": t1 - t0,
            "return_calc_ns": t2 - t1,
            "analytics_ns": t3 - t2,
        }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def run_stac_m3(
    iterations: int = 200_000,
    warmup_iterations: int = 20_000,
    window_size: int = 100,
) -> BenchmarkResult:
    """
    Run STAC-M3: Tick Analytics Benchmark.

    Measures latency of computing real-time analytics (VWAP, SMA, volatility)
    on a stream of market data ticks.
    """
    analytics = TickAnalytics(window_size=window_size)
    tick_stream = analytics._tick_stream
    num_ticks = len(tick_stream)

    # Sub-stage timing accumulators
    window_update_times: list[int] = []
    return_calc_times: list[int] = []
    analytics_times: list[int] = []

    def operation():
        tick = tick_stream[random.randint(0, num_ticks - 1)]
        _, timings = analytics.process_tick_timed(tick)
        window_update_times.append(timings["window_update_ns"])
        return_calc_times.append(timings["return_calc_ns"])
        analytics_times.append(timings["analytics_ns"])
        return None

    def detailed_scoring(stats, iters, duration):
        return compute_score_breakdown(
            stats, iters, duration,
            latency_weight=0.3,
            throughput_weight=0.3,
            jitter_weight=0.1,
            tail_latency_weight=0.15,
            consistency_weight=0.15,
            reference_p50_ns=1200.0,       # FPGA-class tick analytics
            reference_throughput=500_000.0,  # 500K analytics/sec
            reference_jitter_ns=100.0,
            reference_p99_ns=5000.0,
            reference_cv=0.5,
        )

    result = run_benchmark(
        name="STAC-M3",
        version="2.0.0",
        description="Tick Analytics: VWAP, SMA, and volatility computation on tick stream",
        fn=operation,
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        detailed_scoring_fn=detailed_scoring,
        metadata={
            "window_size": window_size,
            "analytics_computed": ["vwap", "sma", "volatility"],
            "sub_stage_timing": {
                "window_update_ns_avg": sum(window_update_times) / len(window_update_times) if window_update_times else 0,
                "return_calc_ns_avg": sum(return_calc_times) / len(return_calc_times) if return_calc_times else 0,
                "analytics_ns_avg": sum(analytics_times) / len(analytics_times) if analytics_times else 0,
            },
            "environment": get_environment_info(),
        },
    )
    return result


if __name__ == "__main__":
    result = run_stac_m3()
    print(result.to_json())
