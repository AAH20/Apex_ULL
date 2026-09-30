# Verification boundary for the September 2026 repair

Local checks on macOS arm64: 96 Python tests, 41 Rust unit/integration tests, C++ feed/matching/UDP GTest suites, and native C exact-once payload stress across MPMC, MPSC and SPMC. GitHub CI additionally runs Linux ThreadSanitizer; consult the actual run outcome rather than inferring it from local stress. The macOS sanitizer runtime could not initialize its allocator on this host, so no local sanitizer success is claimed.

Reproduce from the README commands and enforced CI recipes. Native performance evidence uses batches, includes timer/loop/check overhead, and has no independent calibration. Socket unit tests use loopback; they do not establish a real DPDK or RDMA integration. No board, P&R, exchange, production or official STAC validation was performed.
