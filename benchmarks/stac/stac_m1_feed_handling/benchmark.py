"""
STAC-M1: Feed Handling Benchmark

Measures the latency of processing a single market data tick through a
feed handling pipeline: parse, normalize, and update order book state.

Reference values (from research):
  - FPGA feed handler:        ~200-500 ns per tick
  - Kernel bypass (DPDK):     ~1-5 μs per tick
  - Standard kernel stack:    ~10-50 μs per tick

Scoring: Multi-dimensional composite with:
  - Latency (p50): 40% weight
  - Throughput: 20% weight
  - Jitter: 10% weight
  - Tail latency (p99): 15% weight
  - Consistency (CV): 15% weight
Reference p50: 500 ns (FPGA-class feed handling).
"""

from __future__ import annotations

import struct
import random
from dataclasses import dataclass

from common.harness import (
    run_benchmark,
    BenchmarkResult,
    compute_score_breakdown,
    get_environment_info,
    now_ns,
)
from common.metrics import MetricDef, create_default_registry


# ---------------------------------------------------------------------------
# Benchmark-specific metrics
# ---------------------------------------------------------------------------

STAC_M1_METRICS = [
    MetricDef("parse_ns", "ns", "Tick parsing latency", "lower_is_better", 100.0),
    MetricDef("normalize_ns", "ns", "Tick normalization latency", "lower_is_better", 50.0),
    MetricDef("book_update_ns", "ns", "Order book update latency", "lower_is_better", 200.0),
    MetricDef("ticks_per_second", "ticks/s", "Sustained tick processing rate", "higher_is_better", 1_000_000.0),
    MetricDef("tick_size_bytes", "bytes", "Size of each tick message", "lower_is_better", 64.0),
]


# ---------------------------------------------------------------------------
# Simulated feed handler
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class OrderBookEntry:
    """Single price level in the order book."""
    price: int
    quantity: int


@dataclass(slots=True)
class MarketTick:
    """Normalized market data tick."""
    timestamp_ns: int
    symbol_id: int
    side: int  # 0=bid, 1=ask
    price: int
    quantity: int
    flags: int


class FeedHandler:
    """
    Simulated feed handler pipeline.

    Processes raw binary ticks through:
    1. Parse: deserialize binary tick into structured format
    2. Normalize: convert to internal representation, apply scaling
    3. Book update: insert/update price level in order book
    """

    def __init__(self, num_symbols: int = 100, book_depth: int = 10):
        self.num_symbols = num_symbols
        self.book_depth = book_depth
        # Order books: symbol_id -> list of OrderBookEntry
        self.books: dict[int, list[OrderBookEntry]] = {
            i: [] for i in range(num_symbols)
        }
        # Pre-generate tick templates for realistic processing
        self._tick_templates = self._generate_tick_templates()

    def _generate_tick_templates(self) -> list[bytes]:
        """Generate realistic binary tick messages."""
        templates = []
        for _ in range(1000):
            symbol_id = random.randint(0, self.num_symbols - 1)
            side = random.randint(0, 1)
            price = random.randint(10000, 999999)  # in ticks
            quantity = random.randint(1, 10000)
            timestamp = random.randint(1_000_000_000, 9_999_999_999)
            flags = random.randint(0, 255)
            # Pack: timestamp(8) + symbol_id(4) + side(1) + price(4) + quantity(4) + flags(1) = 22 bytes
            tick = struct.pack("<QIBIIB", timestamp, symbol_id, side, price, quantity, flags)
            templates.append(tick)
        return templates

    def parse_tick(self, raw: bytes) -> MarketTick:
        """Parse raw binary tick into structured format."""
        ts, sym, side, price, qty, flags = struct.unpack("<QIBIIB", raw)
        return MarketTick(
            timestamp_ns=ts,
            symbol_id=sym,
            side=side,
            price=price,
            quantity=qty,
            flags=flags,
        )

    def normalize_tick(self, tick: MarketTick) -> MarketTick:
        """Normalize tick: apply price scaling, validate, and enrich."""
        # Simulate normalization: price scaling (tick -> decimal)
        normalized_price = tick.price * 100  # e.g., 1/100th cent scaling
        # Validate
        if tick.quantity <= 0 or normalized_price <= 0:
            return tick
        return MarketTick(
            timestamp_ns=tick.timestamp_ns,
            symbol_id=tick.symbol_id,
            side=tick.side,
            price=normalized_price,
            quantity=tick.quantity,
            flags=tick.flags,
        )

    def update_book(self, tick: MarketTick) -> None:
        """Update order book with normalized tick."""
        book = self.books.get(tick.symbol_id)
        if book is None:
            return

        # Simple price-level update: find and update or insert
        # In a real system this would be a sorted structure (skip list, etc.)
        found = False
        for entry in book:
            if entry.price == tick.price:
                entry.quantity = tick.quantity
                found = True
                break
        if not found:
            if len(book) < self.book_depth:
                book.append(OrderBookEntry(price=tick.price, quantity=tick.quantity))
            else:
                # Replace worst level (simplified)
                book[random.randint(0, self.book_depth - 1)] = OrderBookEntry(
                    price=tick.price, quantity=tick.quantity
                )

    def process_tick(self, raw: bytes) -> MarketTick:
        """Full feed handling pipeline: parse -> normalize -> book update."""
        tick = self.parse_tick(raw)
        tick = self.normalize_tick(tick)
        self.update_book(tick)
        return tick

    def process_tick_timed(self, raw: bytes) -> tuple[MarketTick, dict[str, int]]:
        """Process tick with per-stage timing."""
        t0 = now_ns()
        tick = self.parse_tick(raw)
        t1 = now_ns()
        tick = self.normalize_tick(tick)
        t2 = now_ns()
        self.update_book(tick)
        t3 = now_ns()
        return tick, {
            "parse_ns": t1 - t0,
            "normalize_ns": t2 - t1,
            "book_update_ns": t3 - t2,
        }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def run_stac_m1(
    iterations: int = 500_000,
    warmup_iterations: int = 50_000,
    num_symbols: int = 100,
) -> BenchmarkResult:
    """
    Run STAC-M1: Feed Handling Benchmark.

    Measures end-to-end latency of processing a single market data tick
    through the feed handling pipeline.
    """
    handler = FeedHandler(num_symbols=num_symbols)
    templates = handler._tick_templates
    num_templates = len(templates)

    # Sub-stage timing accumulators
    parse_times: list[int] = []
    normalize_times: list[int] = []
    book_update_times: list[int] = []

    def operation():
        # Cycle through pre-generated ticks
        raw = templates[random.randint(0, num_templates - 1)]
        _, timings = handler.process_tick_timed(raw)
        parse_times.append(timings["parse_ns"])
        normalize_times.append(timings["normalize_ns"])
        book_update_times.append(timings["book_update_ns"])
        return None

    def detailed_scoring(stats, iters, duration):
        return compute_score_breakdown(
            stats, iters, duration,
            latency_weight=0.4,
            throughput_weight=0.2,
            jitter_weight=0.1,
            tail_latency_weight=0.15,
            consistency_weight=0.15,
            reference_p50_ns=500.0,       # FPGA-class feed handling
            reference_throughput=1_000_000.0,  # 1M ticks/sec
            reference_jitter_ns=50.0,
            reference_p99_ns=2000.0,
            reference_cv=0.3,
        )

    result = run_benchmark(
        name="STAC-M1",
        version="2.0.0",
        description="Feed Handling: parse, normalize, and update order book for a single market data tick",
        fn=operation,
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        detailed_scoring_fn=detailed_scoring,
        metadata={
            "num_symbols": num_symbols,
            "book_depth": handler.book_depth,
            "tick_size_bytes": 22,
            "sub_stage_timing": {
                "parse_ns_avg": sum(parse_times) / len(parse_times) if parse_times else 0,
                "normalize_ns_avg": sum(normalize_times) / len(normalize_times) if normalize_times else 0,
                "book_update_ns_avg": sum(book_update_times) / len(book_update_times) if book_update_times else 0,
            },
            "environment": get_environment_info(),
        },
    )
    return result


if __name__ == "__main__":
    result = run_stac_m1()
    print(result.to_json())
