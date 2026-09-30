"""
STAC-T0: Network I/O Benchmark

Measures the latency of network I/O operations including packet
send/receive, kernel bypass, and RDMA-style operations.

Reference values (from research):
  - FPGA network I/O:          ~100-500 ns
  - Kernel bypass (DPDK):      ~1-5 μs
  - Standard kernel stack:     ~10-50 μs
  - RDMA round-trip:           ~1-3 μs

Scoring: Multi-dimensional composite with:
  - Latency (p50): 35% weight
  - Throughput: 20% weight
  - Jitter: 10% weight
  - Tail latency (p99): 20% weight
  - Consistency (CV): 15% weight
Reference p50: 1000 ns (kernel-bypass class).
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

STAC_T0_METRICS = [
    MetricDef("packet_send_ns", "ns", "Packet send latency", "lower_is_better", 300.0),
    MetricDef("packet_receive_ns", "ns", "Packet receive latency", "lower_is_better", 300.0),
    MetricDef("packet_round_trip_ns", "ns", "Packet round-trip latency", "lower_is_better", 1000.0),
    MetricDef("packets_per_second", "pps", "Sustained packet rate", "higher_is_better", 1_000_000.0),
    MetricDef("packet_size_bytes", "bytes", "Size of each packet", "lower_is_better", 64.0),
]


# ---------------------------------------------------------------------------
# Simulated network I/O
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Packet:
    """Simulated network packet."""
    timestamp_ns: int
    src_port: int
    dst_port: int
    payload: bytes
    checksum: int


class NetworkIO:
    """
    Simulated network I/O with pluggable transport.

    Modes:
      - "kernel_bypass": Simulated DPDK/kernel bypass
      - "rdma": Simulated RDMA
      - "standard": Simulated standard kernel stack
    """

    def __init__(self, mode: str = "kernel_bypass"):
        self.mode = mode
        self._packet_counter = 0
        self._rx_queue: list[Packet] = []
        # Pre-generate packets
        self._packet_templates = self._generate_packets()

    def _generate_packets(self) -> list[Packet]:
        """Generate realistic network packets."""
        packets = []
        for _ in range(1000):
            self._packet_counter += 1
            # Simulate a market data packet: header + payload
            payload = struct.pack("<QIIQII",
                time.perf_counter_ns(),  # timestamp
                random.randint(0, 99),     # symbol_id
                random.randint(0, 1),      # side
                random.randint(10000, 999999),  # price
                random.randint(1, 10000),  # quantity
                0,  # flags
            )
            packets.append(Packet(
                timestamp_ns=time.perf_counter_ns(),
                src_port=random.randint(1024, 65535),
                dst_port=random.randint(1024, 65535),
                payload=payload,
                checksum=random.randint(0, 0xFFFFFFFF),
            ))
        return packets

    def send_packet(self, packet: Packet) -> None:
        """Send a packet through the network."""
        if self.mode == "kernel_bypass":
            # Minimal overhead: direct memory write
            pass
        elif self.mode == "rdma":
            # RDMA: zero-copy, kernel bypass
            pass
        elif self.mode == "standard":
            # Standard: copy to kernel buffer
            _ = bytes(packet.payload)  # Simulate copy

    def receive_packet(self) -> Packet | None:
        """Receive a packet from the network."""
        if self._rx_queue:
            return self._rx_queue.pop(0)
        return None

    def round_trip(self, packet: Packet) -> Packet:
        """Full round-trip: send then receive."""
        self.send_packet(packet)
        # In a real system, this would cross the network
        # Here we simulate by returning the packet
        return packet

    def round_trip_timed(self, packet: Packet) -> tuple[Packet, dict[str, int]]:
        """Round-trip with per-stage timing."""
        t0 = now_ns()
        self.send_packet(packet)
        t1 = now_ns()
        # Simulate network transit
        result = packet
        t2 = now_ns()
        return result, {
            "send_ns": t1 - t0,
            "receive_ns": t2 - t1,
        }

    def process_packet(self, packet: Packet) -> dict:
        """Process a received packet: parse and validate."""
        # Parse payload
        ts, sym, side, price, qty, flags = struct.unpack("<QIIQII", packet.payload)
        # Validate checksum (simplified)
        computed_checksum = sum(packet.payload) & 0xFFFFFFFF
        valid = computed_checksum == packet.checksum
        return {
            "timestamp": ts,
            "symbol_id": sym,
            "side": side,
            "price": price,
            "quantity": qty,
            "valid": valid,
        }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def run_stac_t0(
    iterations: int = 500_000,
    warmup_iterations: int = 50_000,
    mode: str = "kernel_bypass",
) -> BenchmarkResult:
    """
    Run STAC-T0: Network I/O Benchmark.

    Measures latency of network I/O operations including packet
    send/receive and round-trip latency.
    """
    network = NetworkIO(mode=mode)
    templates = network._packet_templates
    num_templates = len(templates)

    # Sub-stage timing accumulators
    send_times: list[int] = []
    receive_times: list[int] = []

    def operation():
        packet = templates[random.randint(0, num_templates - 1)]
        _, timings = network.round_trip_timed(packet)
        send_times.append(timings["send_ns"])
        receive_times.append(timings["receive_ns"])
        return None

    def detailed_scoring(stats, iters, duration):
        return compute_score_breakdown(
            stats, iters, duration,
            latency_weight=0.35,
            throughput_weight=0.2,
            jitter_weight=0.1,
            tail_latency_weight=0.2,
            consistency_weight=0.15,
            reference_p50_ns=1000.0,       # Kernel-bypass class
            reference_throughput=1_000_000.0,  # 1M pps
            reference_jitter_ns=100.0,
            reference_p99_ns=5000.0,
            reference_cv=0.5,
        )

    result = run_benchmark(
        name="STAC-T0",
        version="2.0.0",
        description=f"Network I/O: packet send/receive latency ({mode} transport)",
        fn=operation,
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        detailed_scoring_fn=detailed_scoring,
        metadata={
            "transport_mode": mode,
            "packet_size_bytes": len(templates[0].payload) if templates else 0,
            "sub_stage_timing": {
                "send_ns_avg": sum(send_times) / len(send_times) if send_times else 0,
                "receive_ns_avg": sum(receive_times) / len(receive_times) if receive_times else 0,
            },
            "environment": get_environment_info(),
        },
    )
    return result


if __name__ == "__main__":
    result = run_stac_t0()
    print(result.to_json())
