"""
STAC-T1: Tick-to-Trade Benchmark

Measures the end-to-end latency from receiving a market data tick
to sending an order response, simulating the full tick-to-trade
pipeline.

Reference values (from research):
  - Full FPGA tick-to-trade:    ~150-500 ns
  - Hybrid FPGA+CPU:            ~500 ns - 1 μs
  - Kernel bypass (DPDK):        ~1-5 μs
  - Standard kernel stack:       ~10-50 μs
  - Fastest published:           <25 ns (research benchmark)

Scoring: Multi-dimensional composite with:
  - Latency (p50): 40% weight
  - Throughput: 15% weight
  - Jitter: 5% weight
  - Tail latency (p99): 20% weight
  - Consistency (CV): 20% weight
Reference p50: 500 ns (FPGA-class tick-to-trade).
"""

from __future__ import annotations

import struct
import random
import time
from dataclasses import dataclass

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

STAC_T1_METRICS = [
    MetricDef("tick_processing_ns", "ns", "Tick processing latency", "lower_is_better", 100.0),
    MetricDef("signal_generation_ns", "ns", "Signal generation latency", "lower_is_better", 100.0),
    MetricDef("order_encoding_ns", "ns", "Order encoding latency", "lower_is_better", 100.0),
    MetricDef("tick_to_trade_ns", "ns", "Full tick-to-trade latency", "lower_is_better", 500.0),
    MetricDef("orders_per_second", "orders/s", "Sustained order rate", "higher_is_better", 100_000.0),
]


# ---------------------------------------------------------------------------
# Simulated tick-to-trade pipeline
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Tick:
    """Market data tick."""
    timestamp_ns: int
    symbol_id: int
    side: int  # 0=bid, 1=ask
    price: int
    quantity: int


@dataclass(slots=True)
class Signal:
    """Trading signal generated from tick analysis."""
    symbol_id: int
    action: int  # 0=buy, 1=sell, 2=hold
    confidence: float
    target_price: int
    target_quantity: int


@dataclass(slots=True)
class Order:
    """Encoded order ready for exchange."""
    order_id: int
    symbol_id: int
    side: int  # 0=buy, 1=sell
    price: int
    quantity: int
    order_type: int  # 0=market, 1=limit
    timestamp_ns: int


class TickToTrade:
    """
    Full tick-to-trade pipeline.

    Stages:
    1. Tick processing: parse and normalize incoming tick
    2. Signal generation: analyze tick and generate trading signal
    3. Order encoding: encode order for exchange protocol
    4. Risk check: pre-trade risk validation
    5. Order send: transmit order to exchange
    """

    def __init__(self):
        self._order_counter = 0
        self._tick_templates = self._generate_tick_templates()

    def _generate_tick_templates(self) -> list[Tick]:
        """Generate realistic tick stream."""
        ticks = []
        for _ in range(1000):
            ticks.append(Tick(
                timestamp_ns=time.perf_counter_ns(),
                symbol_id=random.randint(0, 99),
                side=random.randint(0, 1),
                price=random.randint(10000, 999999),
                quantity=random.randint(1, 10000),
            ))
        return ticks

    def process_tick(self, tick: Tick) -> Tick:
        """Stage 1: Parse and normalize tick."""
        # Normalize price to internal representation
        return Tick(
            timestamp_ns=tick.timestamp_ns,
            symbol_id=tick.symbol_id,
            side=tick.side,
            price=tick.price * 100,  # Scale to 1/100th cent
            quantity=tick.quantity,
        )

    def generate_signal(self, tick: Tick) -> Signal:
        """Stage 2: Generate trading signal from tick."""
        # Simplified signal generation: momentum-based
        # In a real system this would use ML models, statistical arbitrage, etc.
        action = 0 if tick.side == 1 else 1  # Buy on ask, sell on bid
        confidence = 0.5 + random.random() * 0.5
        target_price = tick.price
        target_quantity = min(tick.quantity, 1000)  # Cap order size

        return Signal(
            symbol_id=tick.symbol_id,
            action=action,
            confidence=confidence,
            target_price=target_price,
            target_quantity=target_quantity,
        )

    def encode_order(self, signal: Signal) -> Order:
        """Stage 3: Encode order for exchange protocol."""
        self._order_counter += 1
        return Order(
            order_id=self._order_counter,
            symbol_id=signal.symbol_id,
            side=signal.action,
            price=signal.target_price,
            quantity=signal.target_quantity,
            order_type=1,  # Limit order
            timestamp_ns=time.perf_counter_ns(),
        )

    def risk_check(self, order: Order) -> bool:
        """Stage 4: Pre-trade risk check."""
        # Simplified risk check
        if order.quantity <= 0 or order.price <= 0:
            return False
        if order.quantity > 10000:  # Max order size
            return False
        return True

    def send_order(self, order: Order) -> Order:
        """Stage 5: Transmit order to exchange."""
        # In a real system, this would encode to exchange protocol and send
        return order

    def tick_to_trade(self, tick: Tick) -> Order | None:
        """Full tick-to-trade pipeline."""
        # Stage 1: Process tick
        processed = self.process_tick(tick)

        # Stage 2: Generate signal
        signal = self.generate_signal(processed)

        # Stage 3: Encode order
        order = self.encode_order(signal)

        # Stage 4: Risk check
        if not self.risk_check(order):
            return None

        # Stage 5: Send order
        return self.send_order(order)

    def tick_to_trade_timed(self, tick: Tick) -> tuple[Order | None, dict[str, int]]:
        """Full pipeline with per-stage timing."""
        t0 = now_ns()
        processed = self.process_tick(tick)
        t1 = now_ns()
        signal = self.generate_signal(processed)
        t2 = now_ns()
        order = self.encode_order(signal)
        t3 = now_ns()
        risk_ok = self.risk_check(order)
        t4 = now_ns()
        if not risk_ok:
            return None, {
                "tick_processing_ns": t1 - t0,
                "signal_generation_ns": t2 - t1,
                "order_encoding_ns": t3 - t2,
                "risk_check_ns": t4 - t3,
            }
        result = self.send_order(order)
        t5 = now_ns()
        return result, {
            "tick_processing_ns": t1 - t0,
            "signal_generation_ns": t2 - t1,
            "order_encoding_ns": t3 - t2,
            "risk_check_ns": t4 - t3,
            "order_send_ns": t5 - t4,
        }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def run_stac_t1(
    iterations: int = 500_000,
    warmup_iterations: int = 50_000,
) -> BenchmarkResult:
    """
    Run STAC-T1: Tick-to-Trade Benchmark.

    Measures end-to-end latency from receiving a market data tick
    to sending an order response.
    """
    pipeline = TickToTrade()
    templates = pipeline._tick_templates
    num_templates = len(templates)

    # Sub-stage timing accumulators
    tick_processing_times: list[int] = []
    signal_generation_times: list[int] = []
    order_encoding_times: list[int] = []
    risk_check_times: list[int] = []
    order_send_times: list[int] = []

    def operation():
        tick = templates[random.randint(0, num_templates - 1)]
        _, timings = pipeline.tick_to_trade_timed(tick)
        tick_processing_times.append(timings["tick_processing_ns"])
        signal_generation_times.append(timings["signal_generation_ns"])
        order_encoding_times.append(timings["order_encoding_ns"])
        risk_check_times.append(timings["risk_check_ns"])
        if "order_send_ns" in timings:
            order_send_times.append(timings["order_send_ns"])
        return None

    def detailed_scoring(stats, iters, duration):
        return compute_score_breakdown(
            stats, iters, duration,
            latency_weight=0.4,
            throughput_weight=0.15,
            jitter_weight=0.05,
            tail_latency_weight=0.2,
            consistency_weight=0.2,
            reference_p50_ns=500.0,       # FPGA-class tick-to-trade
            reference_throughput=100_000.0,  # 100K orders/sec
            reference_jitter_ns=50.0,
            reference_p99_ns=2000.0,
            reference_cv=0.3,
        )

    result = run_benchmark(
        name="STAC-T1",
        version="2.0.0",
        description="Tick-to-Trade: end-to-end latency from tick reception to order send",
        fn=operation,
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        detailed_scoring_fn=detailed_scoring,
        metadata={
            "pipeline_stages": [
                "tick_processing",
                "signal_generation",
                "order_encoding",
                "risk_check",
                "order_send",
            ],
            "sub_stage_timing": {
                "tick_processing_ns_avg": sum(tick_processing_times) / len(tick_processing_times) if tick_processing_times else 0,
                "signal_generation_ns_avg": sum(signal_generation_times) / len(signal_generation_times) if signal_generation_times else 0,
                "order_encoding_ns_avg": sum(order_encoding_times) / len(order_encoding_times) if order_encoding_times else 0,
                "risk_check_ns_avg": sum(risk_check_times) / len(risk_check_times) if risk_check_times else 0,
                "order_send_ns_avg": sum(order_send_times) / len(order_send_times) if order_send_times else 0,
            },
            "environment": get_environment_info(),
        },
    )
    return result


if __name__ == "__main__":
    result = run_stac_t1()
    print(result.to_json())
