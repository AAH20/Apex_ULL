# Apex_ULL — Ultra-Low Latency Infrastructure

Native software foundations and reproducible CPU baselines for systems where latency, correctness and recovery matter. The research catalogue covers FPGA/ASIC acceleration, kernel bypass, RDMA, networking and domain applications; each implementation keeps its own evidence boundary.

Apex_ULL is the software foundation of the [Apex ecosystem](docs/ecosystem.md). [Apex_Tick](https://github.com/AAH20/Apex_Tick) develops bounded FPGA trading acceleration. [Apex_PerfAtlas](https://github.com/AAH20/Apex_PerfAtlas) validates performance evidence, comparison eligibility and deployment economics. These projects preserve the separate identities of finance, networking, optimization, AI inference and governance in [Ahmed Hassan's portfolio](https://github.com/AAH20).

## Implemented scope

| Area | Executable implementation | Boundary |
|---|---|---|
| C++20 | Feed parser, SPSC ring, matching/order-book components and UDP networking | Component tests; feed DPDK port is explicitly a stub |
| Rust | Feed/channel/parser and matching components | Mock DPDK only; real DPDK and requested thread affinity fail explicitly |
| C queues | SPSC, bounded MPSC/MPMC/SPMC, explicit-mode queue | Per-slot publication/reclamation; no formal lock-free progress guarantee |
| Python | Scheduling, routing, partitioning, arbitrage, data structures and evaluation examples | Research algorithms and synthetic scenarios |
| Hardware/network research | Architecture notes, DPDK/RDMA examples and FPGA tutorials | Not a complete verified hardware product or integrated production backend |

The incomplete Disruptor sequence barrier is unavailable. Auto queue mode now uses a single MPMC queue; switching to SPSC requires a quiescent, empty queue and the single-producer/single-consumer contract. Python queue bindings use aligned storage and rebuild when C sources change.

The C++ order book conserves shared price-level quantity through cancel/modify and rejects duplicate active identities. Nontrivial SPSC elements are constructed and destroyed in their allocated slots. The feed queue retains actual message content and receive timestamps; callback changes require a stopped handler.

## Reproduce correctness

```bash
pip install pytest numpy scipy networkx
python -m pytest tests kernels applications -q --import-mode=importlib
cargo test --locked --manifest-path rust/Cargo.toml

# Install CMake, GoogleTest and Google Benchmark first.
cmake -S cpp/src/feed_handler -B build/feed -DFEED_HANDLER_BUILD_BENCHMARKS=OFF
cmake --build build/feed
ctest --test-dir build/feed --output-on-failure
cmake -S cpp/src/matching_engine -B build/matching -DMATCHING_ENGINE_BUILD_BENCHMARKS=OFF
cmake --build build/matching
ctest --test-dir build/matching --output-on-failure

cc -std=c11 -D_POSIX_C_SOURCE=200809L -O2 -pthread \
  kernels/queue/queue.c kernels/queue/test_queue_native.c -o /tmp/apex-queue-check
/tmp/apex-queue-check
```

CI runs the Python algorithm/application suites, Rust unit/integration tests, C++ feed/matching/UDP suites and native concurrent queues. Linux queue CI includes ThreadSanitizer. A pass is component correctness evidence under the executed conditions, not a production-readiness certificate.

## Native evidence export

```bash
python scripts/export_atlas_run.py --output output/native-host \
  --iterations 10000 --warmup 1000 --batch-size 1024
# After installing Apex_PerfAtlas:
apex-atlas validate output/native-host/run.json
```

The exporter compiles and executes an actual C SPSC probe. It retains chronological batch durations, source/build/config/workload identities, clock metadata, traffic counts and limitations using the Atlas v0.1 contract. The default sample is a batch of 1,024 round trips: batch timing is not individual-operation tail latency. Timer and correctness-check overhead are included. Hardware/affinity/power conditions must be read from the inventory before comparing results.

Receive timestamps qualify for feed latency statistics only when the caller explicitly declares their shared `steady_clock` nanosecond epoch. Zero/unavailable timestamps do not become latency samples. Declared clock resolution is separate from calibrated uncertainty.

## Benchmark claims

The historical [synthetic examples directory](benchmarks/stac/README.md) is not an official STAC implementation. Synthetic network sends, risk examples and Python timings do not establish licensed benchmark compliance. Cross-family rankings, the overall STAC score and the mismatched competitive superiority comparison are withdrawn. Legacy paths/functions remain for compatibility and emitted names identify synthetic examples.

A STAC comparison requires the applicable authorized workload, configuration and metric boundaries; an independent STAC claim requires its actual report. [Public STAC catalogue](https://stacresearch.com/benchmarks/). The June 2024 Exegy/AMD 13.9 ns minimum has a specific actionable-latency boundary and is not an Apex result. [Report announcement](https://docs.stacresearch.com/news/AMD240422).

## Economics and hardware limits

The cost model distinguishes annual incident probability from incident duration and computes constant-cashflow payback from initial investment and annual net cashflow. Power divided by completed operations per second is J/op. Example revenue and costs are assumptions, not observed customer outcomes. [Apex_PerfAtlas](https://github.com/AAH20/Apex_PerfAtlas) provides scoped cost inputs, unknown-value handling and the deployment catalogue.

FPGA, eFPGA, hybrid/custom ASIC, DUV/EUV and colocation discussions remain research or candidate architecture until qualified tools/IP, physical implementation, external calibration and applicable access exist. A board datasheet, clock-cycle calculation or simulation cannot establish end-to-end wire latency.

## Repository navigation

- `cpp/src/feed_handler`, `cpp/src/matching_engine`, `cpp/src/network`: native C++ components.
- `rust`: Rust feed and matching components.
- `kernels`, `applications`: native/Python algorithms and domain examples.
- `benchmarks`, `scripts/export_atlas_run.py`: synthetic examples and retained native measurements.
- `evaluation`, `reports`, `docs`: evaluation models, research and architecture boundaries.
- `.github/workflows`: enforced component checks and native evidence artifacts.

[Review and remaining limitations](docs/implementation-status.md) · [Ecosystem architecture](docs/ecosystem.md).

## License and commercial work

Copyright 2026 Ahmed Hassan. AGPL-3.0-or-later under [LICENSE](LICENSE). Commercial use is permitted under its terms; a separate commercial license can be negotiated where applicable. [NOTICE](NOTICE) adds no author-approval requirement to the AGPL grant. Third-party components retain their licenses. Atlas/Tick use Apache-2.0 for their original code; manifest interoperability does not relicense this repository.

For scoped transport, performance, hardware integration or independent reproduction work: aah@a2zsoc.com. Engagement scope and acceptance evidence determine a contract; no contract value or advanced-environment access is promised by a benchmark claim.

![Architecture with explicit dark cards](docs/ecosystem.svg)

Editable [Mermaid source](docs/ecosystem.mmd). Solid evidence edges identify implemented file interfaces; candidate hardware adapters retain their stated gates.
