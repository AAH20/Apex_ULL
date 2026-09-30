"""
STAC-M2: Messaging Middleware Benchmark

Measures the latency of sending and receiving messages through a
messaging middleware layer, simulating inter-process communication
in a trading system.

Reference values (from research):
  - RDMA / InfiniBand:         ~1-3 μs round-trip
  - DPDK loopback:             ~5-10 μs round-trip
  - Standard TCP loopback:     ~20-50 μs round-trip
  - Shared memory:             ~100-500 ns one-way

Scoring: Multi-dimensional composite with:
  - Latency (p50): 35% weight
  - Throughput: 25% weight
  - Jitter: 10% weight
  - Tail latency (p99): 15% weight
  - Consistency (CV): 15% weight
Reference p50: 2000 ns (RDMA-class round-trip).
"""

from __future__ import annotations

import time
import random
import struct
from dataclasses import dataclass
from collections import deque

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

STAC_M2_METRICS = [
    MetricDef("send_ns", "ns", "Message send latency (one-way)", "lower_is_better", 500.0),
    MetricDef("receive_ns", "ns", "Message receive latency (one-way)", "lower_is_better", 500.0),
    MetricDef("round_trip_ns", "ns", "Full round-trip latency", "lower_is_better", 2000.0),
    MetricDef("messages_per_second", "msg/s", "Sustained message rate", "higher_is_better", 500_000.0),
    MetricDef("message_size_bytes", "bytes", "Size of each message", "lower_is_better", 256.0),
]


# ---------------------------------------------------------------------------
# Simulated messaging middleware
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MarketMessage:
    """Simulated market message."""
    msg_id: int
    timestamp_ns: int
    msg_type: int  # 0=quote, 1=trade, 2=order, 3=cancel
    symbol_id: int
    price: int
    quantity: int


class MessagingMiddleware:
    """
    Simulated messaging middleware with pluggable transport.

    Modes:
      - "shared_memory": In-process queue (lowest latency)
      - "tcp_loopback": Simulated TCP loopback with realistic overhead
      - "rdma": Simulated RDMA with minimal overhead
    """

    def __init__(self, mode: str = "shared_memory", queue_size: int = 1024):
        self.mode = mode
        self.queue_size = queue_size
        self._queue: deque[MarketMessage] = deque(maxlen=queue_size)
        self._msg_counter = 0
        # Pre-generate messages
        self._msg_templates = self._generate_messages()

    def _generate_messages(self) -> list[MarketMessage]:
        """Generate realistic market messages."""
        msgs = []
        for _ in range(1000):
            self._msg_counter += 1
            msgs.append(MarketMessage(
                msg_id=self._msg_counter,
                timestamp_ns=time.perf_counter_ns(),
                msg_type=random.randint(0, 3),
                symbol_id=random.randint(0, 99),
                price=random.randint(10000, 999999),
                quantity=random.randint(1, 10000),
            ))
        return msgs

    def send(self, msg: MarketMessage) -> None:
        """Send a message through the middleware."""
        if self.mode == "shared_memory":
            # Direct queue append - minimal overhead
            self._queue.append(msg)
        elif self.mode == "tcp_loopback":
            # Simulate TCP overhead: serialization + copy
            serialized = struct.pack("<QIIQII",
                msg.msg_id, msg.timestamp_ns, msg.msg_type,
                msg.symbol_id, msg.price, msg.quantity)
            self._queue.append(msg)
        elif self.mode == "rdma":
            # Simulate RDMA: minimal serialization, direct memory access
            self._queue.append(msg)

    def receive(self) -> MarketMessage | None:
        """Receive a message from the middleware."""
        if self._queue:
            return self._queue.popleft()
        return None

    def round_trip(self, msg: MarketMessage) -> MarketMessage:
        """Full round-trip: send then receive."""
        self.send(msg)
        # In a real system, this would cross process/network boundary
        # Here we simulate the round-trip by processing the queue
        result = self.receive()
        if result is None:
            # Should not happen in single-threaded simulation
            result = msg
        return result

    def round_trip_timed(self, msg: MarketMessage) -> tuple[MarketMessage, dict[str, int]]:
        """Round-trip with per-stage timing."""
        t0 = now_ns()
        self.send(msg)
        t1 = now_ns()
        result = self.receive()
        t2 = now_ns()
        if result is None:
            result = msg
        return result, {
            "send_ns": t1 - t0,
            "receive_ns": t2 - t1,
        }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def run_stac_m2(
    iterations: int = 200_000,
    warmup_iterations: int = 20_000,
    mode: str = "shared_memory",
) -> BenchmarkResult:
    """
    Run STAC-M2: Messaging Middleware Benchmark.

    Measures round-trip latency of sending and receiving market messages
    through a messaging middleware layer.
    """
    middleware = MessagingMiddleware(mode=mode)
    templates = middleware._msg_templates
    num_templates = len(templates)

    # Sub-stage timing accumulators
    send_times: list[int] = []
    receive_times: list[int] = []

    def operation():
        msg = templates[random.randint(0, num_templates - 1)]
        _, timings = middleware.round_trip_timed(msg)
        send_times.append(timings["send_ns"])
        receive_times.append(timings["receive_ns"])
        return None

    def detailed_scoring(stats, iters, duration):
        return compute_score_breakdown(
            stats, iters, duration,
            latency_weight=0.35,
            throughput_weight=0.25,
            jitter_weight=0.1,
            tail_latency_weight=0.15,
            consistency_weight=0.15,
            reference_p50_ns=2000.0,       # RDMA-class round-trip
            reference_throughput=500_000.0,  # 500K msg/sec
            reference_jitter_ns=200.0,
            reference_p99_ns=10000.0,
            reference_cv=0.5,
        )

    result = run_benchmark(
        name="STAC-M2",
        version="2.0.0",
        description=f"Messaging Middleware: round-trip message latency ({mode} transport)",
        fn=operation,
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        detailed_scoring_fn=detailed_scoring,
        metadata={
            "transport_mode": mode,
            "queue_size": middleware.queue_size,
            "message_size_bytes": 28,  # struct.pack("<QIIQII") = 8+4+4+4+4+4 = 28
            "sub_stage_timing": {
                "send_ns_avg": sum(send_times) / len(send_times) if send_times else 0,
                "receive_ns_avg": sum(receive_times) / len(receive_times) if receive_times else 0,
            },
            "environment": get_environment_info(),
        },
    )
    return result


if __name__ == "__main__":
    result = run_stac_m2()
    print(result.to_json())
